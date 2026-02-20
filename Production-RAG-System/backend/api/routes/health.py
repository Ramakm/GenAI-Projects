from fastapi import APIRouter

from api.models.response import HealthResponse
from config import OLLAMA_MODEL, EMBEDDING_MODEL
from core.llm import check_ollama
from core.vectorstore import get_chunk_count, is_loaded, list_documents

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check() -> HealthResponse:
    """Return the operational status of every system component."""
    ollama_ok = check_ollama()
    vs_loaded = is_loaded()
    total_chunks = get_chunk_count()
    total_docs = len(list_documents())

    if ollama_ok and vs_loaded:
        status = "healthy"
        detail = None
    elif ollama_ok:
        status = "degraded"
        detail = "Vector store not yet loaded (no documents uploaded)"
    else:
        status = "unhealthy"
        detail = "Cannot reach Ollama service"

    return HealthResponse(
        status=status,
        ollama_connected=ollama_ok,
        ollama_model=OLLAMA_MODEL,
        embedding_model=EMBEDDING_MODEL,
        total_chunks=total_chunks,
        total_documents=total_docs,
        vectorstore_loaded=vs_loaded,
        detail=detail,
    )
