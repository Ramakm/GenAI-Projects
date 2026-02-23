import logging

import httpx
from langchain_ollama import ChatOllama

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)


def get_llm() -> ChatOllama:
    return ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=LLM_TEMPERATURE,
    )


def check_ollama() -> dict:
    """Check Ollama connectivity and model availability."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                model_available = any(OLLAMA_MODEL in m for m in models)
                return {
                    "ollama_connected": True,
                    "model_available": model_available,
                    "model": OLLAMA_MODEL,
                    "available_models": models,
                }
            return {"ollama_connected": False, "model_available": False, "model": OLLAMA_MODEL}
    except Exception as e:
        logger.warning(f"Ollama check failed: {e}")
        return {"ollama_connected": False, "model_available": False, "model": OLLAMA_MODEL, "error": str(e)}
