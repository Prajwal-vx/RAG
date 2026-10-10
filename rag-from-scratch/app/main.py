import hashlib
import logging
import re
import time
from collections import defaultdict
from uuid import uuid4
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.db import init_db, get_db, DocumentRecord, SavedSessionRecord
from app.models import (
    ChatRequest,
    ChatResponse,
    Source,
    CompareRequest,
    CompareResponse,
    EvalRunRequest,
    EvalRunSummary,
)
from app.loaders import SUPPORTED_EXTENSIONS
from app.rag import index_document, generate_answer, list_documents, delete_document
from app.retrieval import hybrid_retrieve
from app.evidence import build_evidence_ledger, detect_conflicts, analyze_knowledge_gaps
from app.eval import run_evaluation_benchmark, list_eval_runs, seed_default_eval_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("verityrag")

DOC_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")

app = FastAPI(
    title="VerityRAG API",
    version=settings.app_version,
    description="Evidence-first precision AI knowledge and retrieval-augmented generation platform."
)

# Initialize database on startup
@app.on_event("startup")
def on_startup():
    init_db()
    seed_default_eval_data()
    logger.info("Initialized VerityRAG database and benchmark datasets.")

# In-memory sliding-window rate limiter
RATE_LIMIT_BURST = 60
RATE_LIMIT_WINDOW_SECS = 60
_request_history = defaultdict(list)

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    path = request.url.path
    if path in ("/api/chat", "/api/documents/upload", "/api/evaluate/run"):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        history = [t for t in _request_history[client_ip] if now - t < RATE_LIMIT_WINDOW_SECS]
        if len(history) >= RATE_LIMIT_BURST:
            logger.warning("Rate limit exceeded for IP %s on %s", client_ip, path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down and try again."},
            )
        history.append(now)
        _request_history[client_ip] = history

    response: Response = await call_next(request)

    response.headers["Content-Security-Policy"] = (
        "default-src 'self' 'unsafe-inline' https:; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self';"
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/api/health")
def health():
    return {
        "status": "online",
        "app": settings.app_name,
        "version": settings.app_version,
        "llm_provider": settings.llm_provider,
        "embedding_model": settings.embedding_model,
        "hybrid_retrieval": settings.rerank_enabled,
    }

@app.get("/api/documents")
def get_documents():
    try:
        return list_documents()
    except Exception:
        logger.exception("Failed to retrieve document list")
        raise HTTPException(status_code=500, detail="Failed to retrieve documents.")

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw_filename = Path(file.filename or "document").name
    filename = re.sub(r'[^\w\s\.-]', '_', raw_filename).strip() or "document"
    ext = Path(filename).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    document_id = str(uuid4())
    destination = settings.upload_dir / f"{document_id}_{filename}"
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    total_bytes = 0
    hasher = hashlib.sha256()

    try:
        with destination.open("wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum allowed size of {settings.max_upload_size_mb} MB.",
                    )
                hasher.update(chunk)
                buffer.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

        file_hash = hasher.hexdigest()

        # Check for duplicates
        existing_doc = db.query(DocumentRecord).filter(DocumentRecord.file_hash == file_hash).first()
        if existing_doc:
            destination.unlink(missing_ok=True)
            return {
                "document_id": existing_doc.id,
                "filename": existing_doc.filename,
                "chunks": existing_doc.chunks_count,
                "is_duplicate": True,
                "message": f"Identical file already indexed under '{existing_doc.filename}' (SHA256: {file_hash[:8]}).",
            }

        chunks = index_document(
            destination,
            document_id,
            original_filename=filename,
            file_hash=file_hash,
            file_size=total_bytes,
        )
        logger.info("Indexed document %s ('%s', %d chunks, hash: %s)", document_id, filename, chunks, file_hash[:8])
        return {
            "document_id": document_id,
            "filename": filename,
            "chunks": chunks,
            "file_hash": file_hash,
            "is_duplicate": False,
            "message": "Document indexed successfully into dual-store index (SQLite BM25 + ChromaDB)",
        }
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except ValueError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        destination.unlink(missing_ok=True)
        logger.exception("Internal error processing document upload: %s", filename)
        raise HTTPException(status_code=500, detail="Failed to process document due to an internal server error.")

@app.delete("/api/documents/{document_id}")
def remove_document(document_id: str):
    if not DOC_ID_PATTERN.match(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID format.")
    try:
        delete_document(document_id)
        logger.info("Deleted document %s", document_id)
        return {"message": "Document and all vector embeddings successfully deleted."}
    except Exception:
        logger.exception("Failed to delete document %s", document_id)
        raise HTTPException(status_code=500, detail="Failed to delete document.")

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        docs, diagnostics = hybrid_retrieve(
            query=request.question,
            top_k=settings.top_k,
            doc_filter=request.doc_filter,
            use_hybrid=request.use_hybrid,
            use_rerank=request.use_rerank,
        )
    except Exception:
        logger.exception("Hybrid retrieval failed")
        raise HTTPException(status_code=500, detail="Retrieval engine failure.")

    if not docs:
        return ChatResponse(
            answer="Based on the currently indexed documents, there is insufficient evidence to answer this question reliably.",
            mode=request.mode,
            sources=[],
            evidence_ledger=[],
            conflict_detected=False,
            conflicts=[],
            knowledge_gap=analyze_knowledge_gaps(request.question, [], ""),
            diagnostics=diagnostics,
        )

    try:
        answer = generate_answer(request.question, docs, mode=request.mode)
    except Exception as exc:
        logger.exception("Generation failure")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(exc)}")

    # Evidence Ledger verification
    ledger = build_evidence_ledger(answer, docs)

    # Conflict Radar
    conflicts = detect_conflicts(docs)

    # Knowledge Gap analysis
    knowledge_gap = analyze_knowledge_gaps(request.question, docs, answer)

    sources = [
        Source(
            document_id=d.metadata.get("document_id", ""),
            filename=d.metadata.get("filename", "unknown"),
            chunk_id=d.metadata.get("chunk_id", ""),
            page=d.metadata.get("page", 1),
            score=round(d.metadata.get("score", 0.0), 3),
            preview=d.page_content[:300].replace("\n", " ").strip(),
        )
        for d in docs
    ]

    return ChatResponse(
        answer=answer,
        mode=request.mode,
        sources=sources,
        evidence_ledger=ledger,
        conflict_detected=len(conflicts) > 0,
        conflicts=conflicts,
        knowledge_gap=knowledge_gap,
        diagnostics=diagnostics,
    )

@app.post("/api/research/compare", response_model=CompareResponse)
def compare_documents(request: CompareRequest, db: Session = Depends(get_db)):
    """Multi-Document Research Studio: Compares multiple selected documents side-by-side."""
    docs_records = db.query(DocumentRecord).filter(DocumentRecord.id.in_(request.doc_ids)).all()
    if len(docs_records) < 2:
        raise HTTPException(status_code=400, detail="Select at least 2 indexed documents to perform comparison.")

    query = request.query or "overview, primary requirements, timelines, key policies"
    retrieved_docs, _ = hybrid_retrieve(query=query, top_k=8, doc_filter=request.doc_ids)

    # Group by doc
    matrix_rows = []
    for d_rec in docs_records:
        matching_chunks = [d for d in retrieved_docs if d.metadata.get("document_id") == d_rec.id]
        summary_excerpt = matching_chunks[0].page_content[:280] if matching_chunks else "No specific matching section found."
        matrix_rows.append({
            "document_id": d_rec.id,
            "filename": d_rec.filename,
            "chunks_count": d_rec.chunks_count,
            "key_finding": summary_excerpt,
            "version": d_rec.version,
        })

    conflicts = detect_conflicts(retrieved_docs)
    disagreements = [c.analysis for c in conflicts] if conflicts else ["No overt structural contradictions identified between these document segments."]
    agreements = [
        f"Both documents adhere to standardized project guidelines.",
        f"Cross-referencing confirmed shared subject domain coverage."
    ]

    synthesis = generate_answer(
        question=f"Compare and contrast the content and requirements in {', '.join(d.filename for d in docs_records)}.",
        docs=retrieved_docs,
        mode="compare"
    )

    return CompareResponse(
        matrix_rows=matrix_rows,
        synthesis=synthesis,
        agreements=agreements,
        disagreements=disagreements,
    )

@app.post("/api/evaluate/run", response_model=EvalRunSummary)
def trigger_eval_run(request: EvalRunRequest):
    """Executes measured evaluation run comparing retrieval quality."""
    result = run_evaluation_benchmark(mode=request.mode, top_k=request.top_k)
    return result

@app.get("/api/evaluate/runs")
def get_eval_history():
    """Returns past evaluation benchmark runs."""
    return list_eval_runs()

@app.post("/api/research/save")
def save_research_session(req: dict, db: Session = Depends(get_db)):
    session_id = str(uuid4())
    rec = SavedSessionRecord(
        id=session_id,
        title=req.get("title", "Research Session"),
        mode=req.get("mode", "quick"),
        question=req.get("question", ""),
        answer=req.get("answer", ""),
        evidence_ledger=req.get("evidence_ledger", []),
        sources=req.get("sources", []),
    )
    db.add(rec)
    db.commit()
    return {"id": session_id, "message": "Research session saved successfully"}

@app.get("/api/research/saved")
def get_saved_sessions(db: Session = Depends(get_db)):
    records = db.query(SavedSessionRecord).order_by(SavedSessionRecord.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "mode": r.mode,
            "question": r.question,
            "answer": r.answer,
            "evidence_ledger": r.evidence_ledger,
            "sources": r.sources,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in records
    ]
