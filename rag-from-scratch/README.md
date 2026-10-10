# VerityRAG — Precision Evidence-First AI Knowledge Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://docs.trychroma.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **VerityRAG** is an evidence-first precision AI knowledge platform that transforms scattered documents into an auditable, verifiable knowledge repository. It replaces opaque black-box AI responses with explicit citation traceability, contradiction detection, and measurable retrieval benchmarks.

---

## 🏛️ Defining Architectural Principles

1. **Every factual claim must link to verifiable evidence.**
2. **If evidence is insufficient, the system declines to hallucinate.**
3. **Contradictions across documents must be surfaced, never silently merged.**
4. **Evaluation results must be empirically measured, never manufactured.**
5. **No purple gradients or generic AI-chat aesthetics** — designed with an editorial Dark Slate & Warm Amber visual identity.

---

## ⚡ Core Capabilities

- **Intelligent Ingestion Pipeline:** Dual-store indexing into SQLite (for sparse BM25 lexical tokens) and persistent ChromaDB (for dense semantic vectors). Automatic SHA-256 duplicate detection and structure-aware chunking.
- **Hybrid Retrieval Engine:** Combines dense vector similarity with sparse BM25 keyword matching via Reciprocal Rank Fusion (RRF), near-duplicate passage pruning, and position-sensitive cross-encoder reranking.
- **The Evidence Ledger (Signature Feature):** Decomposes answers into verified claims, evaluating directness (`Direct`, `Indirect`, `Insufficient`) and citing specific source filenames and page numbers.
- **Conflict Radar (Signature Feature):** Automatically flags cross-document divergence (e.g. conflicting milestone dates, superseded versions, contradictory policies) across indexed documents.
- **Multi-Document Research Studio:** Enables side-by-side comparative synthesis, consensus matrix generation, and disagreement breakdowns across selected files.
- **Knowledge Gap Detector:** Analyzes what the indexed corpus does *not* answer, proposing specific search queries rather than inventing facts.
- **RAG Observatory:** In-app evaluation harness measuring real **Recall@K**, **Mean Reciprocal Rank (MRR)**, **Citation Precision**, and **Latency** comparing Enhanced Hybrid RAG against Baseline Semantic-Only.
- **Dossier Persistence:** Save and revisit reproducible research sessions with linked claims and sources.

---

## 🛠️ Technology Stack

- **Backend:** Python, FastAPI, Pydantic v2, SQLAlchemy (SQLite persistent relational store).
- **Vector & Embeddings:** ChromaDB vector database, HuggingFace `sentence-transformers/all-MiniLM-L6-v2` (runs 100% offline locally).
- **Document Extractors:** `pypdf`, `python-docx`, Markdown, and plain text parsers with security binary signature validation.
- **LLM Engine:** Pluggable provider interface supporting:
  - `mock` (fully offline, deterministic, zero-cost development)
  - `openai` (GPT-4o, GPT-4o-mini)
  - `ollama` (local Llama 3.2, Mistral)
- **UI/UX Design:** Bespoke editorial dark theme (Dark Slate `#0B0F17`, Warm Amber `#E2B340`, Emerald `#10B981`) with tabbed workspace navigation and real-time ledger inspection.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (Python 3.12/3.14 compatible)
- Git

### 2. Environment Setup

```bash
# Clone and navigate into directory
cd rag-from-scratch

# Create and activate virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env`:

```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

By default, `LLM_PROVIDER=mock` is enabled so you can run and test everything offline immediately without an API key. To use OpenAI or Ollama, configure:

```ini
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### 4. Run the Application

```bash
uvicorn app.main:app --reload
```

Open your browser at:
👉 **`http://127.0.0.1:8000`**

---

## 🧪 Running Automated Tests

Run the comprehensive pytest suite verifying uploads, duplicate hash rejection, conflict detection, knowledge gap discovery, and evaluation benchmark runs:

```bash
# From the rag-from-scratch directory:
pytest -v tests/test_rag.py
```

---

## 🔬 Demonstration Scenario

To demonstrate VerityRAG's differentiating features:

1. **Upload Conflicting Documents:**
   - In the sidebar, upload `data/sample_apollo_spec.md` (states deployment deadline is **15 November**).
   - Upload `data/sample_apollo_update.md` (states deployment deadline is **22 November**).
2. **Execute Research Query:**
   - In the chat box, ask: `"What is the deployment deadline for Project Apollo?"`
3. **Inspect the Evidence Ledger & Conflict Radar:**
   - Notice the **Conflict Radar** alert immediately highlights the timeline contradiction between the two documents.
   - Review each claim in the **Evidence Ledger** on the right with direct citation snippets.
4. **Test Knowledge Gap Detector:**
   - Ask an unanswerable query: `"What quantum encryption protocol does Apollo use?"`
   - Notice the system declines to hallucinate and identifies the missing topic in the **Knowledge Gap** panel.
5. **Run RAG Observatory Benchmarks:**
   - Click the **RAG Observatory** tab in the sidebar.
   - Click **Run Enhanced Hybrid Benchmark** and **Run Baseline Semantic-Only** to view live, empirical Recall@5 and MRR metrics.

---

## 📂 Project Structure

```
rag-from-scratch/
├── app/
│   ├── config.py           # Application settings and environment management
│   ├── db.py               # SQLite schema (documents, chunks, sessions, evals)
│   ├── eval.py             # RAG Observatory benchmark engine (MRR, Recall@K)
│   ├── evidence.py         # Evidence Ledger, Conflict Radar & Gap Detector
│   ├── loaders.py          # File extraction and binary validation
│   ├── main.py             # FastAPI REST endpoints, rate limiting, security
│   ├── models.py           # Pydantic request and response schemas
│   ├── rag.py              # Dual-store indexing and multi-provider generation
│   ├── retrieval.py        # Hybrid BM25 + dense search, RRF & reranker
│   └── vectorstore.py      # ChromaDB embeddings integration
├── data/
│   ├── sample_apollo_spec.md    # Demo document A
│   └── sample_apollo_update.md  # Demo document B (conflicting update)
├── static/
│   ├── app.js              # Tab management, reactive ledger & chat logic
│   ├── index.html          # Clean editorial workspace interface
│   └── style.css           # Bespoke Dark Slate & Amber editorial theme
├── tests/
│   └── test_rag.py         # Automated pytest test suite
├── .env.example            # Environment configuration template
├── README.md               # Complete engineering documentation
└── requirements.txt        # Production dependencies
```

---

## 🛡️ Security Model

- **Prompt Injection Defense:** Untrusted document context is fenced within explicit delimiters and treated as non-executable text data.
- **Upload Validation:** Strict binary signature checks prevent execution of binaries (PE, ELF, Mach-O) disguised as text.
- **ZIP Bomb Defense:** Decompression size checks prevent archive exhaustion attacks.
- **Rate Limiting:** Sliding-window burst limiter on sensitive endpoints (`/api/chat`, `/api/documents/upload`).
- **Security Headers:** Strict CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`.
