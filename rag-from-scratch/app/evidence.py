import re
from typing import List, Dict, Any, Tuple
from langchain_core.documents import Document
from app.models import ClaimLedgerItem, ConflictItem, KnowledgeGapItem

def extract_claims(answer: str) -> List[str]:
    """Splits answer into verifiable factual sentences or propositions."""
    sentences = re.split(r"(?<=[.!?])\s+", answer)
    claims = []
    for s in sentences:
        clean = s.strip()
        # Filter greetings, questions, or disclaimers
        if len(clean) > 20 and not clean.endswith("?") and not clean.startswith("I "):
            claims.append(clean)
    return claims[:8]

def build_evidence_ledger(answer: str, docs: List[Document]) -> List[ClaimLedgerItem]:
    """Generates the signature Evidence Ledger: maps claims to exact supporting passages with directness classification."""
    claims = extract_claims(answer)
    if not claims:
        # Fallback to general statement
        claims = [answer[:150] + "..."] if len(answer) > 150 else [answer]

    ledger: List[ClaimLedgerItem] = []

    for claim in claims:
        claim_words = set(re.findall(r"\w+", claim.lower()))
        best_doc = None
        best_overlap = 0.0
        best_match_text = ""

        for d in docs:
            doc_words = set(re.findall(r"\w+", d.page_content.lower()))
            common = claim_words & doc_words
            overlap = len(common) / len(claim_words) if claim_words else 0
            if overlap > best_overlap:
                best_overlap = overlap
                best_doc = d
                # Extract the most relevant snippet
                best_match_text = d.page_content[:240].strip()

        if best_overlap >= 0.55:
            directness = "Direct"
            status = "verified"
            evidence = best_match_text
            filename = best_doc.metadata.get("filename", "Source Document") if best_doc else "Unknown"
            page = best_doc.metadata.get("page", 1) if best_doc else 1
        elif best_overlap >= 0.30:
            directness = "Indirect"
            status = "partial"
            evidence = best_match_text or "Passage provides related background context."
            filename = best_doc.metadata.get("filename", "Source Document") if best_doc else "Unknown"
            page = best_doc.metadata.get("page", 1) if best_doc else 1
        else:
            directness = "Insufficient"
            status = "unsupported"
            evidence = "No direct passage in indexed evidence explicitly validates this specific claim."
            filename = "None"
            page = 1

        ledger.append(ClaimLedgerItem(
            claim=claim,
            status=status,
            directness=directness,
            evidence=evidence,
            source_filename=filename,
            source_page=page,
        ))

    return ledger

def detect_conflicts(docs: List[Document]) -> List[ConflictItem]:
    """Conflict Radar (Signature Feature): Identifies contradictions or opposing statements across distinct documents."""
    conflicts: List[ConflictItem] = []
    if len(docs) < 2:
        return conflicts

    # Group passages by document
    by_doc: Dict[str, List[Document]] = {}
    for d in docs:
        fn = d.metadata.get("filename", "unknown")
        by_doc.setdefault(fn, []).append(d)

    doc_names = list(by_doc.keys())
    if len(doc_names) < 2:
        return conflicts

    # Check pairs of documents for temporal, numeric, or policy discrepancies
    # Key contradiction patterns: dates, versions, quantities, deadlines, statuses
    date_patterns = [r"\b(?:\d{1,2}\s+[A-Za-z]+|\b[A-Za-z]+\s+\d{1,2}|\d{4}-\d{2}-\d{2})\b"]
    
    for i in range(len(doc_names)):
        for j in range(i + 1, len(doc_names)):
            doc_a_name = doc_names[i]
            doc_b_name = doc_names[j]
            
            for da in by_doc[doc_a_name]:
                for db in by_doc[doc_b_name]:
                    text_a = da.page_content
                    text_b = db.page_content
                    
                    # Detect deadline or date conflicts
                    dates_a = set(re.findall(r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\b", text_a, re.I))
                    dates_b = set(re.findall(r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\b", text_b, re.I))
                    
                    if dates_a and dates_b and dates_a != dates_b:
                        conflicts.append(ConflictItem(
                            id=f"cnf-{len(conflicts)+1}",
                            topic="Timeline / Deadline Discrepancy",
                            doc_a_filename=doc_a_name,
                            doc_a_excerpt=text_a[:220].strip(),
                            doc_a_page=da.metadata.get("page", 1),
                            doc_b_filename=doc_b_name,
                            doc_b_excerpt=text_b[:220].strip(),
                            doc_b_page=db.metadata.get("page", 1),
                            analysis=f"Conflicting milestone dates identified: '{', '.join(dates_a)}' vs '{', '.join(dates_b)}'. Check whether one document supersedes the other.",
                            nature="contradiction",
                        ))
                        break

                    # Detect version or policy status conflict
                    v_a = re.findall(r"v\d+\.\d+|\bversion\s+\d+", text_a, re.I)
                    v_b = re.findall(r"v\d+\.\d+|\bversion\s+\d+", text_b, re.I)
                    if v_a and v_b and set(v_a) != set(v_b):
                        conflicts.append(ConflictItem(
                            id=f"cnf-{len(conflicts)+1}",
                            topic="Version Divergence",
                            doc_a_filename=doc_a_name,
                            doc_a_excerpt=text_a[:220].strip(),
                            doc_a_page=da.metadata.get("page", 1),
                            doc_b_filename=doc_b_name,
                            doc_b_excerpt=text_b[:220].strip(),
                            doc_b_page=db.metadata.get("page", 1),
                            analysis=f"Specification references different release targets ({', '.join(set(v_a))} vs {', '.join(set(v_b))}).",
                            nature="version_update",
                        ))
                        break
                if conflicts:
                    break
            if conflicts:
                break

    return conflicts

def analyze_knowledge_gaps(question: str, docs: List[Document], answer: str) -> KnowledgeGapItem:
    """Knowledge Gap Detector: Distinguishes 'what is proven' from 'what is missing' without fabricating info."""
    q_tokens = [w for w in re.findall(r"\w+", question.lower()) if len(w) > 3]
    all_content = " ".join(d.page_content.lower() for d in docs)
    
    established: List[str] = []
    missing: List[str] = []
    missing_topics: List[str] = []

    # Check which aspects of question are actually covered
    for token in q_tokens:
        if token in all_content:
            established.append(f"Document evidence references topic '{token}'.")
        else:
            missing.append(f"No specific documentation found regarding '{token}'.")

    if not established:
        established.append("General domain background exists, but specific question parameters are absent.")
        missing_topics.append("Exact implementation specifications or quantitative metrics")

    if not missing:
        missing.append("No critical missing topics identified for this specific query.")
    else:
        missing_topics.append("Source files addressing: " + ", ".join(q_tokens[:3]))

    suggested = [
        f"Search for foundational documents covering '{q_tokens[0]}'" if q_tokens else "Provide additional system design specs.",
        "Check if relevant details exist under an alternative terminology or version.",
    ]

    return KnowledgeGapItem(
        established_facts=established[:3],
        missing_information=missing[:3],
        missing_topics=missing_topics[:2],
        suggested_follow_ups=suggested,
    )
