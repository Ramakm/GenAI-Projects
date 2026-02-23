import asyncio
import json
import logging

from agents.state import RegulatoryAnalysisState
from core.llm import get_llm
from core.pdf_loader import extract_text_from_pdf
from core.web_scraper import scrape_url
from core.rss_poller import fetch_feed_entries

logger = logging.getLogger(__name__)

_METADATA_PROMPT = """Extract regulatory document metadata from the following text.
Return ONLY a valid JSON object with exactly these keys:
{{
  "regulation_name": "Full official name of the regulation or document",
  "issuing_body": "Name of the regulatory authority or issuer",
  "effective_date": "Effective or implementation date (ISO format or descriptive)",
  "jurisdiction": "Geographic or sectoral jurisdiction"
}}
Use null for any field you cannot determine.

TEXT:
{text}

JSON:"""


def _extract_metadata(text: str) -> dict:
    """Call LLM to extract structured metadata from document header."""
    llm = get_llm()
    snippet = text[:2000]
    prompt = _METADATA_PROMPT.format(text=snippet)
    try:
        response = llm.invoke(prompt)
        raw = response.content.strip()
        # Strip markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        data = json.loads(raw)
        return {
            "regulation_name": data.get("regulation_name"),
            "issuing_body": data.get("issuing_body"),
            "effective_date": data.get("effective_date"),
            "jurisdiction": data.get("jurisdiction"),
        }
    except Exception as e:
        logger.warning(f"Metadata extraction failed: {e}")
        return {
            "regulation_name": None,
            "issuing_body": None,
            "effective_date": None,
            "jurisdiction": None,
        }


def parse_document(state: RegulatoryAnalysisState) -> RegulatoryAnalysisState:
    """Node 1: Parse the input document and extract text + metadata."""
    source_type = state["source_type"]
    raw_content = state["raw_content"]
    source_identifier = state["source_identifier"]

    progress = list(state.get("progress_messages", []))
    progress.append(f"Node 1 (Document Parser): Processing {source_type} input — {source_identifier}")

    try:
        if source_type == "pdf":
            file_bytes = raw_content.encode("latin-1") if isinstance(raw_content, str) else raw_content
            parsed_text = extract_text_from_pdf(file_bytes)
        elif source_type == "url":
            parsed_text = asyncio.get_event_loop().run_until_complete(scrape_url(raw_content))
        elif source_type == "text":
            parsed_text = raw_content.strip()
        elif source_type == "rss":
            entries = fetch_feed_entries(raw_content, max_entries=1)
            if entries:
                parsed_text = entries[0]["full_text"]
            else:
                parsed_text = raw_content
        else:
            parsed_text = raw_content.strip()

        progress.append(f"Extracted {len(parsed_text)} characters of text")

    except Exception as e:
        logger.error(f"Document parsing failed: {e}")
        return {
            **state,
            "parsed_text": None,
            "current_agent": "document_parser",
            "progress_messages": progress,
            "error": f"Document parsing failed: {e}",
        }

    metadata = _extract_metadata(parsed_text)
    progress.append(
        f"Metadata: regulation='{metadata['regulation_name']}', "
        f"issuer='{metadata['issuing_body']}'"
    )

    return {
        **state,
        "parsed_text": parsed_text,
        "regulation_name": metadata["regulation_name"],
        "issuing_body": metadata["issuing_body"],
        "effective_date": metadata["effective_date"],
        "jurisdiction": metadata["jurisdiction"],
        "current_agent": "document_parser",
        "progress_messages": progress,
    }
