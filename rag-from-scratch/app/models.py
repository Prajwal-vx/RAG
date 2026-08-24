from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=10000)

class Source(BaseModel):
    document_id: str
    filename: str
    chunk_id: str
    preview: str

class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
