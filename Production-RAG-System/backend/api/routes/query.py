from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.models.request import QueryRequest, StreamQueryRequest
from api.models.response import QueryResponse, SourceDocument
from core.rag_chain import run_rag_query, run_rag_stream
from core.vectorstore import is_loaded

router = APIRouter(prefix="/api/query", tags=["Query"])


def _ensure_vectorstore_loaded() -> None:
    if not is_loaded():
        raise HTTPException(
            status_code=503,
            detail="No documents have been indexed yet. Upload a document first.",
        )


@router.post("", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    """Answer a question using the RAG pipeline (blocking)."""
    _ensure_vectorstore_loaded()

    try:
        result = run_rag_query(
            question=request.question,
            top_k=request.top_k,
            filter_source=request.filter_source,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}")

    sources = [SourceDocument(**s) for s in result["sources"]]
    return QueryResponse(
        answer=result["answer"],
        sources=sources,
        model_used=result["model_used"],
        chunks_retrieved=result["chunks_retrieved"],
        question=result["question"],
    )


@router.post("/stream")
def query_stream(request: StreamQueryRequest) -> StreamingResponse:
    """Answer a question using the RAG pipeline with SSE streaming."""
    _ensure_vectorstore_loaded()

    return StreamingResponse(
        run_rag_stream(question=request.question, top_k=request.top_k),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
