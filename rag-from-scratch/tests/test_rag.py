import pytest
import io
from fastapi.testclient import TestClient
from pathlib import Path
from app.main import app
from app.retrieval import reciprocal_rank_fusion, cross_encoder_rerank, deduplicate_passages
from app.evidence import extract_claims, build_evidence_ledger, detect_conflicts, analyze_knowledge_gaps
from langchain_core.documents import Document

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "app" in data

def test_upload_and_retrieve_flow():
    # 1. Upload sample text document
    sample_content = b"# Architecture Overview\nProject Apollo uses hybrid retrieval combining BM25 and vector embeddings."
    files = {"file": ("test_arch.md", io.BytesIO(sample_content), "text/markdown")}
    upload_res = client.post("/api/documents/upload", files=files)
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    doc_id = upload_data["document_id"]
    assert upload_data["chunks"] >= 1

    # 2. Verify in list
    docs_res = client.get("/api/documents")
    assert docs_res.status_code == 200
    docs = docs_res.json()
    assert any(d["document_id"] == doc_id for d in docs)

    # 3. Chat query
    chat_res = client.post("/api/chat", json={
        "question": "What does Project Apollo use?",
        "mode": "quick",
        "use_hybrid": True
    })
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "answer" in chat_data
    assert len(chat_data["sources"]) > 0
    assert len(chat_data["evidence_ledger"]) > 0

    # 4. Clean up
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200

def test_duplicate_detection():
    content = b"Exact duplicate testing content with unique hash identifier."
    files1 = {"file": ("dup1.txt", io.BytesIO(content), "text/plain")}
    res1 = client.post("/api/documents/upload", files=files1)
    assert res1.status_code == 200
    doc_id1 = res1.json()["document_id"]

    # Upload exact duplicate
    files2 = {"file": ("dup2.txt", io.BytesIO(content), "text/plain")}
    res2 = client.post("/api/documents/upload", files=files2)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2.get("is_duplicate") is True

    # Cleanup
    client.delete(f"/api/documents/{doc_id1}")

def test_conflict_radar_detection():
    doc1 = Document(
        page_content="The deployment deadline is 15 November according to initial roadmap.",
        metadata={"filename": "spec_v1.md", "page": 1}
    )
    doc2 = Document(
        page_content="The deployment deadline is 22 November following leadership revision.",
        metadata={"filename": "spec_v2.md", "page": 1}
    )

    conflicts = detect_conflicts([doc1, doc2])
    assert len(conflicts) > 0
    assert conflicts[0].nature in ("contradiction", "version_update")
    assert "15 November" in conflicts[0].analysis or "22 November" in conflicts[0].analysis

def test_knowledge_gap_detector():
    doc = Document(
        page_content="System supports user authorization and database persistence.",
        metadata={"filename": "doc.md", "page": 1}
    )
    # Question asks for completely unindexed feature
    gap = analyze_knowledge_gaps("quantum cryptography encryption", [doc], "Answer")
    assert len(gap.missing_information) > 0
    assert any("cryptography" in m or "quantum" in m for m in gap.missing_information)

def test_eval_benchmark_suite():
    res = client.post("/api/evaluate/run", json={"mode": "enhanced", "top_k": 3})
    assert res.status_code == 200
    data = res.json()
    assert "recall_at_k" in data
    assert "mrr" in data
    assert "citation_precision" in data
    assert "avg_latency_ms" in data
