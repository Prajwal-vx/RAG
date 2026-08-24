from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.config import settings
from app.vectorstore import get_vectorstore
from app.loaders import load_file

SYSTEM_PROMPT = '''You are a Retrieval-Augmented Generation assistant.
Answer ONLY from the retrieved context below.
If the context does not contain enough information, clearly say:
"I don't have enough information in the indexed documents to answer that."
Do not invent facts. Be concise but useful.
'''

def index_document(path, document_id: str) -> int:
    docs = load_file(path, document_id)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(docs)

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"{document_id}:{i}"

    ids = [chunk.metadata["chunk_id"] for chunk in chunks]
    get_vectorstore().add_documents(chunks, ids=ids)
    return len(chunks)

def retrieve(question: str) -> list[Document]:
    return get_vectorstore().similarity_search(question, k=settings.top_k)

def generate_answer(question: str, docs: list[Document]) -> str:
    context = "\n\n".join(
        f"[Source: {d.metadata.get('filename')} | Chunk: {d.metadata.get('chunk_id')}]\n{d.page_content}"
        for d in docs
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Retrieved context:\n{context}\n\nQuestion: {question}"},
    ]

    provider = settings.llm_provider.lower()

    if provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is missing in .env")
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0,
        )
        return response.choices[0].message.content or ""

    if provider == "ollama":
        import urllib.request, json
        payload = json.dumps({
            "model": settings.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0},
        }).encode()
        req = urllib.request.Request(
            settings.ollama_base_url.rstrip("/") + "/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as res:
            data = json.loads(res.read().decode())
        return data["message"]["content"]

    raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")

def list_documents():
    collection = get_vectorstore().get(include=["metadatas"])
    grouped = {}
    for metadata in collection.get("metadatas", []):
        doc_id = metadata.get("document_id")
        if not doc_id:
            continue
        grouped.setdefault(doc_id, {
            "document_id": doc_id,
            "filename": metadata.get("filename", "unknown"),
            "chunks": 0,
        })
        grouped[doc_id]["chunks"] += 1
    return list(grouped.values())

def delete_document(document_id: str):
    store = get_vectorstore()
    result = store.get(where={"document_id": document_id})
    ids = result.get("ids", [])
    if ids:
        store.delete(ids=ids)
