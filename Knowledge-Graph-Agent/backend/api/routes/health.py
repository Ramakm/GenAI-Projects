from fastapi import APIRouter
from core.llm import check_ollama
from api.models.response import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    info = check_ollama()
    status = "healthy" if info["ollama_connected"] and info["model_available"] else "degraded"
    return HealthResponse(
        status=status,
        ollama_connected=info["ollama_connected"],
        model_available=info["model_available"],
        model=info["model"],
    )
