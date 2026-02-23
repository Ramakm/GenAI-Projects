from fastapi import APIRouter

from api.models.response import HealthResponse
from core.llm import check_ollama

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    ollama_info = await check_ollama()
    status = "healthy" if ollama_info["connected"] else "degraded"
    return HealthResponse(
        status=status,
        ollama_connected=ollama_info["connected"],
        model_available=ollama_info["model_available"],
        available_models=ollama_info["available_models"],
        version="1.0.0",
        service="Regulatory Impact Analysis Agent",
    )
