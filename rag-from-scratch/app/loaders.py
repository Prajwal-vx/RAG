from pathlib import Path
from langchain_core.documents import Document
from pypdf import PdfReader
from docx import Document as DocxDocument

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}

def load_file(path: Path, document_id: str) -> list[Document]:
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    if ext == ".pdf":
        reader = PdfReader(str(path))
        docs = []
        for page_no, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "document_id": document_id,
                        "filename": path.name,
                        "page": page_no,
                    },
                ))
        return docs

    if ext == ".docx":
        docx = DocxDocument(str(path))
        text = "\n".join(p.text for p in docx.paragraphs if p.text.strip())
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")

    return [Document(
        page_content=text,
        metadata={"document_id": document_id, "filename": path.name, "page": 1},
    )]
