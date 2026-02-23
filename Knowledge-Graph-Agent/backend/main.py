import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, LOG_LEVEL, CORS_ORIGINS
from api.routes.health import router as health_router
from api.routes.graph import router as graph_router
from api.routes.query import router as query_router

logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Knowledge Graph Agent backend...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                if any(OLLAMA_MODEL in m for m in models):
                    logger.info(f"Model '{OLLAMA_MODEL}' is available in Ollama.")
                else:
                    logger.warning(f"Model '{OLLAMA_MODEL}' not found. Run: ollama pull {OLLAMA_MODEL}")
            else:
                logger.warning(f"Ollama returned status {resp.status_code}")
    except Exception as e:
        logger.warning(f"Could not reach Ollama at startup: {e}")
    yield
    logger.info("Shutting down Knowledge Graph Agent.")


app = FastAPI(
    title="Knowledge Graph Agent",
    description="5-node LangGraph pipeline: Document Ingester → Entity Extractor → Relationship Extractor → Graph Builder → Graph Summarizer",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(graph_router, prefix="/api")
app.include_router(query_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "service": "Knowledge Graph Agent",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
