from typing import List, Optional
from pydantic import BaseModel


class SourceDocument(BaseModel):
    content: str
    source: str
    doc_id: str
    chunk_index: int
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]
    model_used: str
    chunks_retrieved: int
    question: str


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    chunk_count: int
    uploaded_at: str
    file_size_bytes: int


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int
    message: str


class DeleteResponse(BaseModel):
    doc_id: str
    filename: str
    message: str


class HealthResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    ollama_connected: bool
    ollama_model: str
    embedding_model: str
    total_chunks: int
    total_documents: int
    vectorstore_loaded: bool
    detail: Optional[str] = None
