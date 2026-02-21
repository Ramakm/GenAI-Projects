import httpx
from fastapi import APIRouter

from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from api.models.response import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    ollama_connected = False
    model_available = False
    available_models: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                ollama_connected = True
                models_data = resp.json().get("models", [])
                available_models = [m["name"] for m in models_data]
                model_available = any(OLLAMA_MODEL in m for m in available_models)
    except Exception:
        pass

    status = "healthy" if ollama_connected else "degraded"

    return HealthResponse(
        status=status,
        ollama_connected=ollama_connected,
        model_available=model_available,
        available_models=available_models,
    )
