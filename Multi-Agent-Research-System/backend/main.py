from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging

from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from api.routes.health import router as health_router
from api.routes.research import router as research_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warmup: verify Ollama is reachable and model is available
    logger.info("Starting Multi-Agent Research System backend...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                if any(OLLAMA_MODEL in m for m in models):
                    logger.info(f"Model '{OLLAMA_MODEL}' is available in Ollama.")
                else:
                    logger.warning(
                        f"Model '{OLLAMA_MODEL}' not found. "
                        f"Run: docker exec ollama ollama pull {OLLAMA_MODEL}"
                    )
            else:
                logger.warning(f"Ollama returned status {resp.status_code}")
    except Exception as e:
        logger.warning(f"Could not reach Ollama at startup: {e}")
    yield
    logger.info("Shutting down backend.")


app = FastAPI(
    title="Multi-Agent Research System",
    description="Three-agent pipeline: Source Gatherer → Citation Verifier → Report Writer",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(research_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "service": "Multi-Agent Research System",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
