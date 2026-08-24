from functools import lru_cache
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from app.config import settings

COLLECTION_NAME = "rag_documents"

@lru_cache
def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        encode_kwargs={"normalize_embeddings": True},
    )

@lru_cache
def get_vectorstore():
    return Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=str(settings.chroma_dir),
        embedding_function=get_embeddings(),
    )
