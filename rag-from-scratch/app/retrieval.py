import re
import math
import time
from typing import List, Dict, Any, Tuple
from collections import Counter
from langchain_core.documents import Document
from app.config import settings
from app.vectorstore import get_vectorstore
from app.db import SessionLocal, ChunkRecord

def tokenize(text: str) -> List[str]:
    """Tokenize and normalize text for lexical matching."""
    return re.findall(r"\w+", text.lower())

def compute_bm25_score(query_tokens: List[str], doc_tokens: List[str], avg_doc_len: float, num_docs: int, df: Dict[str, int]) -> float:
    """Calculates BM25 score for a document given query terms."""
    k1 = 1.5
    b = 0.75
    doc_len = len(doc_tokens)
    score = 0.0
    tf_counts = Counter(doc_tokens)

    for term in query_tokens:
        if term not in tf_counts:
            continue
        freq = tf_counts[term]
        doc_freq = df.get(term, 0)
        # Standard BM25 IDF
        idf = math.log((num_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
        numerator = freq * (k1 + 1)
        denominator = freq + k1 * (1 - b + b * (doc_len / (avg_doc_len or 1)))
        score += idf * (numerator / denominator)

    return score

def lexical_search(query: str, top_k: int = 10, doc_filter: List[str] = None) -> List[Tuple[Document, float]]:
    """Performs BM25 lexical keyword search across chunks in database."""
    session = SessionLocal()
    try:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        q = session.query(ChunkRecord)
        if doc_filter:
            q = q.filter(ChunkRecord.document_id.in_(doc_filter))
        all_chunks = q.all()
        if not all_chunks:
            return []

        num_docs = len(all_chunks)
        total_tokens = 0
        df = Counter()
        chunk_tokenized = []

        for chunk in all_chunks:
            tokens = tokenize(chunk.content)
            chunk_tokenized.append((chunk, tokens))
            total_tokens += len(tokens)
            unique_terms = set(tokens)
            for term in query_tokens:
                if term in unique_terms:
                    df[term] += 1

        avg_doc_len = total_tokens / num_docs if num_docs > 0 else 1.0

        scored = []
        for chunk, tokens in chunk_tokenized:
            score = compute_bm25_score(query_tokens, tokens, avg_doc_len, num_docs, df)
            if score > 0:
                doc = Document(
                    page_content=chunk.content,
                    metadata={
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "filename": chunk.document.filename if chunk.document else "unknown",
                        "page": chunk.page_number,
                    }
                )
                scored.append((doc, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
    finally:
        session.close()

def semantic_search(query: str, top_k: int = 10, doc_filter: List[str] = None) -> List[Tuple[Document, float]]:
    """Performs dense vector similarity search via ChromaDB."""
    store = get_vectorstore()
    filter_dict = None
    if doc_filter and len(doc_filter) == 1:
        filter_dict = {"document_id": doc_filter[0]}
    elif doc_filter:
        filter_dict = {"document_id": {"$in": doc_filter}}

    results = store.similarity_search_with_relevance_scores(query, k=top_k, filter=filter_dict)
    return [(doc, float(score)) for doc, score in results]

def reciprocal_rank_fusion(
    semantic_results: List[Tuple[Document, float]],
    lexical_results: List[Tuple[Document, float]],
    k_constant: int = 60,
    weight_semantic: float = 0.65,
    weight_lexical: float = 0.35,
) -> List[Tuple[Document, float]]:
    """Fuses ranked lists using Reciprocal Rank Fusion (RRF)."""
    scores: Dict[str, float] = {}
    doc_map: Dict[str, Document] = {}

    for rank, (doc, _) in enumerate(semantic_results):
        cid = doc.metadata.get("chunk_id") or doc.page_content[:64]
        doc_map[cid] = doc
        scores[cid] = scores.get(cid, 0.0) + weight_semantic * (1.0 / (k_constant + rank + 1))

    for rank, (doc, _) in enumerate(lexical_results):
        cid = doc.metadata.get("chunk_id") or doc.page_content[:64]
        doc_map[cid] = doc
        scores[cid] = scores.get(cid, 0.0) + weight_lexical * (1.0 / (k_constant + rank + 1))

    sorted_cids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [(doc_map[cid], scores[cid]) for cid in sorted_cids]

def cross_encoder_rerank(query: str, candidates: List[Document], top_k: int = 5) -> List[Document]:
    """Lightweight Cross-Encoder style reranking based on query term density and position."""
    if not candidates:
        return []

    q_terms = set(tokenize(query))
    scored = []
    for doc in candidates:
        c_text = doc.page_content.lower()
        # Coverage score
        matched = sum(1 for term in q_terms if term in c_text)
        coverage_ratio = matched / (len(q_terms) or 1)
        # Exact substring reward
        exact_bonus = 0.5 if query.lower() in c_text else 0.0
        # Position bonus (earlier mentions get slight boost)
        earliest_pos = min([c_text.find(term) for term in q_terms if term in c_text] or [99999])
        pos_bonus = 0.2 if earliest_pos < 100 else 0.0

        total_score = coverage_ratio + exact_bonus + pos_bonus
        scored.append((doc, total_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in scored[:top_k]]

def deduplicate_passages(docs: List[Document], similarity_threshold: float = 0.85) -> List[Document]:
    """Removes near-duplicate passages to maximize diverse evidence in context window."""
    unique_docs: List[Document] = []
    seen_token_sets = []

    for doc in docs:
        tokens = set(tokenize(doc.page_content))
        if not tokens:
            continue
        is_dup = False
        for existing in seen_token_sets:
            # Jaccard similarity
            intersection = len(tokens & existing)
            union = len(tokens | existing)
            jaccard = intersection / union if union > 0 else 0
            if jaccard >= similarity_threshold:
                is_dup = True
                break
        if not is_dup:
            unique_docs.append(doc)
            seen_token_sets.append(tokens)

    return unique_docs

def hybrid_retrieve(
    query: str,
    top_k: int = 5,
    doc_filter: List[str] = None,
    use_hybrid: bool = True,
    use_rerank: bool = True,
) -> Tuple[List[Document], Dict[str, Any]]:
    """Orchestrates multi-stage retrieval: Query Decomposition -> Hybrid Search -> RRF -> Deduplication -> Reranking."""
    t0 = time.time()
    
    # 1. Candidate retrieval
    semantic_top = semantic_search(query, top_k=top_k * 2, doc_filter=doc_filter)
    lexical_top = lexical_search(query, top_k=top_k * 2, doc_filter=doc_filter) if use_hybrid else []

    # 2. Fusion
    if use_hybrid and lexical_top:
        fused = reciprocal_rank_fusion(
            semantic_top,
            lexical_top,
            weight_semantic=settings.hybrid_weight_semantic,
            weight_lexical=settings.hybrid_weight_lexical,
        )
        candidates = [doc for doc, _ in fused]
    else:
        candidates = [doc for doc, _ in semantic_top]

    # 3. Deduplication
    deduped = deduplicate_passages(candidates)

    # 4. Reranking
    if use_rerank and deduped:
        final_docs = cross_encoder_rerank(query, deduped, top_k=top_k)
    else:
        final_docs = deduped[:top_k]

    t1 = time.time()
    diagnostics = {
        "method": "Hybrid (Semantic + Lexical BM25 + RRF + Reranker)" if use_hybrid else "Semantic-Only",
        "semantic_hits": len(semantic_top),
        "lexical_hits": len(lexical_top),
        "fused_candidates": len(candidates),
        "deduped_count": len(deduped),
        "reranked_top_k": len(final_docs),
        "latency_ms": round((t1 - t0) * 1000, 2),
    }

    return final_docs, diagnostics
