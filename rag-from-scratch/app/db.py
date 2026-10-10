import hashlib
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Boolean,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.config import settings

DATABASE_URL = f"sqlite:///{settings.db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DocumentRecord(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_hash = Column(String, index=True, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    chunks_count = Column(Integer, default=0)
    version = Column(Integer, default=1)
    status = Column(String, default="completed")  # queued, processing, completed, failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    chunks = relationship("ChunkRecord", back_populates="document", cascade="all, delete-orphan")

class ChunkRecord(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True, index=True)  # e.g. doc_id:0
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, default=1)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    document = relationship("DocumentRecord", back_populates="chunks")

class SavedSessionRecord(Base):
    __tablename__ = "saved_sessions"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    mode = Column(String, default="standard")
    question = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    evidence_ledger = Column(JSON, default=list)
    sources = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class EvalDatasetRecord(Base):
    __tablename__ = "eval_dataset"

    id = Column(String, primary_key=True, index=True)
    question = Column(String, nullable=False)
    ground_truth = Column(Text, nullable=False)
    expected_doc_keywords = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class EvalRunRecord(Base):
    __tablename__ = "eval_runs"

    id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    mode = Column(String, nullable=False)  # baseline vs enhanced
    total_samples = Column(Integer, default=0)
    recall_at_k = Column(Float, default=0.0)
    mrr = Column(Float, default=0.0)
    faithfulness_score = Column(Float, default=0.0)
    citation_precision = Column(Float, default=0.0)
    avg_latency_ms = Column(Float, default=0.0)
    details = Column(JSON, default=list)

def init_db():
    Base.metadata.create_all(bind=engine)

# Auto-initialize database on import
init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
