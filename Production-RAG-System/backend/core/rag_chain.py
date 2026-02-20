import json
from typing import Dict, Generator, List, Optional

from core.llm import get_langchain_llm, stream_ollama
from core.retriever import format_context, retrieve_with_scores
from config import OLLAMA_MODEL, TOP_K

GROUNDED_PROMPT = """You are a helpful assistant that answers questions strictly based on the provided context.

Rules:
- Answer ONLY using information found in the context below.
- If the answer is not present in the context, say: "I don't have enough information in the provided documents to answer this question."
- Cite the source number (e.g. [Source 1]) when referencing information.
- Be concise and accurate.

Context:
{context}

Question: {question}

Answer:"""


def run_rag_query(
    question: str,
    top_k: Optional[int] = None,
    filter_source: Optional[str] = None,
) -> Dict:
    """Run a full RAG pipeline and return a structured result dict."""
    results = retrieve_with_scores(question, top_k=top_k or TOP_K, filter_source=filter_source)
    context = format_context(results)

    prompt = GROUNDED_PROMPT.format(context=context, question=question)

    llm = get_langchain_llm()
    response = llm.invoke(prompt)
    answer = response.content if hasattr(response, "content") else str(response)

    sources = []
    for doc, score in results:
        sources.append(
            {
                "content": doc.page_content,
                "source": doc.metadata.get("filename", doc.metadata.get("source", "unknown")),
                "doc_id": doc.metadata.get("doc_id", ""),
                "chunk_index": doc.metadata.get("chunk_index", 0),
                "score": float(score),
            }
        )

    return {
        "answer": answer,
        "sources": sources,
        "model_used": OLLAMA_MODEL,
        "chunks_retrieved": len(results),
        "question": question,
    }


def run_rag_stream(
    question: str,
    top_k: Optional[int] = None,
) -> Generator[str, None, None]:
    """Run the RAG pipeline and yield SSE-formatted events.

    Event flow:
      1. data: {"event": "sources", "sources": [...]}
      2. data: {"event": "token", "token": "..."}  (repeated)
      3. data: {"event": "done"}
    """
    results = retrieve_with_scores(question, top_k=top_k or TOP_K)
    context = format_context(results)

    # Emit sources first (great UX: user sees what was retrieved before generation starts)
    sources = []
    for doc, score in results:
        sources.append(
            {
                "content": doc.page_content,
                "source": doc.metadata.get("filename", doc.metadata.get("source", "unknown")),
                "doc_id": doc.metadata.get("doc_id", ""),
                "chunk_index": doc.metadata.get("chunk_index", 0),
                "score": float(score),
            }
        )

    yield f"data: {json.dumps({'event': 'sources', 'sources': sources})}\n\n"

    # Stream tokens
    prompt = GROUNDED_PROMPT.format(context=context, question=question)
    for token in stream_ollama(prompt):
        yield f"data: {json.dumps({'event': 'token', 'token': token})}\n\n"

    yield f"data: {json.dumps({'event': 'done'})}\n\n"
