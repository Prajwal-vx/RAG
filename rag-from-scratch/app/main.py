import shutil
from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, settings
from app.models import ChatRequest, ChatResponse, Source
from app.loaders import SUPPORTED_EXTENSIONS
from app.rag import index_document, retrieve, generate_answer, list_documents, delete_document

app = FastAPI(title="RAG From Scratch", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/api/health")
def health():
    return {"status": "ok", "provider": settings.llm_provider}

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    filename = Path(file.filename or "document").name
    ext = Path(filename).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file. Use: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    document_id = str(uuid4())
    destination = settings.upload_dir / f"{document_id}_{filename}"

    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        chunks = index_document(destination, document_id)
        return {
            "document_id": document_id,
            "filename": filename,
            "chunks": chunks,
            "message": "Document indexed successfully",
        }
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/documents")
def documents():
    return list_documents()

@app.delete("/api/documents/{document_id}")
def remove_document(document_id: str):
    delete_document(document_id)
    return {"message": "Document deleted"}

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    docs = retrieve(request.question)

    if not docs:
        return ChatResponse(
            answer="I don't have enough information in the indexed documents to answer that.",
            sources=[],
        )

    try:
        answer = generate_answer(request.question, docs)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    sources = [
        Source(
            document_id=d.metadata.get("document_id", ""),
            filename=d.metadata.get("filename", "unknown"),
            chunk_id=d.metadata.get("chunk_id", ""),
            preview=d.page_content[:280].replace("\n", " "),
        )
        for d in docs
    ]

    return ChatResponse(answer=answer, sources=sources)
