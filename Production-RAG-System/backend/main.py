from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import documents, health, query
from core.embeddings import get_embeddings
from core.vectorstore import load_vectorstore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warmup tasks run once at startup before the first request is served."""
    # Pre-load the embedding model into the lru_cache (avoids 30-60s cold-start)
    get_embeddings()

    # Load the persisted FAISS index (no-op if no documents indexed yet)
    load_vectorstore()

    yield
    # (no shutdown cleanup needed)


app = FastAPI(
    title="Production RAG API",
    description="A production-grade Retrieval-Augmented Generation API backed by Ollama + FAISS.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the Streamlit frontend (and Swagger UI) to call this API from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(documents.router)
app.include_router(query.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Production RAG API is running",
        "docs": "/docs",
        "health": "/health",
    }
