from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "VerityRAG"
    app_version: str = "2.0.0"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_provider: str = "mock"  # mock | openai | ollama
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    top_k: int = 5
    chunk_size: int = 900
    chunk_overlap: int = 150
    max_upload_size_mb: int = 50
    rerank_enabled: bool = True
    hybrid_weight_semantic: float = 0.65
    hybrid_weight_lexical: float = 0.35

    @property
    def upload_dir(self) -> Path:
        p = BASE_DIR / "data" / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def chroma_dir(self) -> Path:
        p = BASE_DIR / "data" / "chroma"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def db_path(self) -> Path:
        p = BASE_DIR / "data" / "verityrag.db"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

settings = Settings()
