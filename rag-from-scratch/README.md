# RAG From Scratch

A complete Retrieval-Augmented Generation application.

## Features

- Upload PDF, TXT, MD, and DOCX files
- Extract and split document text
- Create local semantic embeddings
- Store vectors in persistent ChromaDB
- Search relevant chunks
- Send retrieved context to an LLM
- Return grounded answers with source citations
- View indexed documents and delete them
- OpenAI and Ollama support
- FastAPI backend + browser chat UI

## Quick start

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and configure your provider.

Run:

```bash
uvicorn app.main:app --reload
```

Open:

`http://127.0.0.1:8000`

## Architecture

Upload -> Parse -> Split -> Embed -> ChromaDB

Question -> Embed -> Semantic Search -> Top-K Context -> LLM -> Answer + Sources

## API

- `GET /api/health`
- `POST /api/documents/upload`
- `GET /api/documents`
- `DELETE /api/documents/{document_id}`
- `POST /api/chat`
