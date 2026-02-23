import httpx
from langchain_ollama import ChatOllama

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, LLM_TEMPERATURE


def get_llm() -> ChatOllama:
    return ChatOllama(
        model=OLLAMA_MODEL,
        temperature=LLM_TEMPERATURE,
        base_url=OLLAMA_BASE_URL,
    )


async def check_ollama() -> dict:
    """Check Ollama connectivity and model availability."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                available_models = [m["name"] for m in data.get("models", [])]
                model_available = any(OLLAMA_MODEL in m for m in available_models)
                return {
                    "connected": True,
                    "model_available": model_available,
                    "available_models": available_models,
                }
    except Exception:
        pass
    return {
        "connected": False,
        "model_available": False,
        "available_models": [],
    }
