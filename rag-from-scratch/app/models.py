from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=10000)
    mode: str = Field(default="quick")  # quick, detailed, compare, structured, beginner
    doc_filter: Optional[List[str]] = None
    use_hybrid: bool = True
    use_rerank: bool = True

class Source(BaseModel):
    document_id: str
    filename: str
    chunk_id: str
    page: int = 1
    score: float = 0.0
    preview: str

class ClaimLedgerItem(BaseModel):
    claim: str
    status: str  # verified, partial, unsupported
    directness: str  # Direct, Indirect, Insufficient
    evidence: str
    source_filename: str
    source_page: int = 1
    conflicts: Optional[str] = None

class ConflictItem(BaseModel):
    id: str
    topic: str
    doc_a_filename: str
    doc_a_excerpt: str
    doc_a_page: int
    doc_b_filename: str
    doc_b_excerpt: str
    doc_b_page: int
    analysis: str
    nature: str  # contradiction, version_update, scope_divergence

class KnowledgeGapItem(BaseModel):
    established_facts: List[str]
    missing_information: List[str]
    missing_topics: List[str]
    suggested_follow_ups: List[str]

class RetrievalDiagnostic(BaseModel):
    method: str
    semantic_hits: int
    lexical_hits: int
    fused_candidates: int
    reranked_top_k: int
    deduped_count: int
    latency_ms: float

class ChatResponse(BaseModel):
    answer: str
    mode: str
    sources: List[Source]
    evidence_ledger: List[ClaimLedgerItem]
    conflict_detected: bool = False
    conflicts: List[ConflictItem] = []
    knowledge_gap: Optional[KnowledgeGapItem] = None
    diagnostics: Optional[RetrievalDiagnostic] = None

class CompareRequest(BaseModel):
    doc_ids: List[str] = Field(min_length=2, max_length=5)
    query: Optional[str] = None

class CompareResponse(BaseModel):
    matrix_rows: List[Dict[str, Any]]
    synthesis: str
    agreements: List[str]
    disagreements: List[str]

class EvalRunRequest(BaseModel):
    mode: str = "enhanced"  # baseline or enhanced
    top_k: int = 5

class EvalRunSummary(BaseModel):
    id: str
    timestamp: str
    mode: str
    total_samples: int
    recall_at_k: float
    mrr: float
    faithfulness_score: float
    citation_precision: float
    avg_latency_ms: float
    details: List[Dict[str, Any]]
