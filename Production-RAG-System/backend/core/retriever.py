from typing import List, Optional, Tuple

from langchain.schema import Document

from config import TOP_K
from core.vectorstore import get_faiss_instance


def retrieve_with_scores(
    question: str,
    top_k: Optional[int] = None,
    filter_source: Optional[str] = None,
) -> List[Tuple[Document, float]]:
    """Run similarity search and return (document, score) pairs.

    Lower L2 distance = higher relevance. Scores are NOT probabilities.
    """
    vs = get_faiss_instance()
    if vs is None:
        return []

    k = top_k or TOP_K
    results: List[Tuple[Document, float]] = vs.similarity_search_with_score(question, k=k)

    if filter_source:
        results = [
            (doc, score)
            for doc, score in results
            if doc.metadata.get("filename") == filter_source
            or doc.metadata.get("source") == filter_source
        ]

    return results


def format_context(results: List[Tuple[Document, float]]) -> str:
    """Format retrieved chunks into a numbered context block for the prompt."""
    if not results:
        return "No relevant context found."

    blocks = []
    for i, (doc, score) in enumerate(results, start=1):
        source = doc.metadata.get("filename", doc.metadata.get("source", "unknown"))
        chunk_idx = doc.metadata.get("chunk_index", "?")
        blocks.append(
            f"[Source {i}] {source} (chunk {chunk_idx}, distance={score:.4f})\n"
            f"{doc.page_content.strip()}"
        )

    return "\n\n---\n\n".join(blocks)
