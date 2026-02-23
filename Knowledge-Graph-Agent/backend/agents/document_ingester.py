import logging
import re

import httpx
from bs4 import BeautifulSoup

from agents.state import KnowledgeGraphState
from config import CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNKS

logger = logging.getLogger(__name__)


def _clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _chunk_text(text: str) -> list:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def _fetch_url(url: str) -> str:
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def document_ingester(state: KnowledgeGraphState) -> KnowledgeGraphState:
    logger.info("Node 1: document_ingester — parsing and chunking document")
    messages = list(state.get("progress_messages", []))
    messages.append("Ingesting document...")

    source_type = state.get("source_type", "text")
    raw_content = state.get("raw_content", "")
    source_identifier = state.get("source_identifier", "inline")

    try:
        if source_type == "url":
            messages.append(f"Fetching URL: {source_identifier}")
            parsed_text = _fetch_url(source_identifier if source_identifier != "inline" else raw_content)
        else:
            parsed_text = raw_content

        parsed_text = _clean_text(parsed_text)
        all_chunks = _chunk_text(parsed_text)
        chunks = all_chunks[:MAX_CHUNKS]
        char_count = len(parsed_text)

        messages.append(
            f"Parsed {char_count:,} chars → {len(chunks)} chunks "
            f"({'truncated from ' + str(len(all_chunks)) if len(all_chunks) > MAX_CHUNKS else 'all chunks'})"
        )

        return {
            **state,
            "parsed_text": parsed_text,
            "text_chunks": chunks,
            "char_count": char_count,
            "current_agent": "document_ingester",
            "progress_messages": messages,
        }
    except Exception as e:
        logger.error(f"document_ingester failed: {e}")
        messages.append(f"Ingestion error: {e}")
        return {
            **state,
            "parsed_text": raw_content,
            "text_chunks": [raw_content[:CHUNK_SIZE]] if raw_content else [],
            "char_count": len(raw_content),
            "current_agent": "document_ingester",
            "progress_messages": messages,
            "error": str(e),
        }
