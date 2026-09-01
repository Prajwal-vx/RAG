from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"  # FIXED: Changed from gpt-4.1-mini
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"  # FIXED: Changed from llama3.2 to more common llama2
    top_k: int = 5
    chunk_size: int = 900
    chunk_overlap: int = 150
    environment: str = "development"
    max_upload_size_mb: int = 50

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

settings = Settings()
