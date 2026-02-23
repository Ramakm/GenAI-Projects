import logging
import re
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.models.request import URLIngestRequest, TextIngestRequest, RSSIngestRequest
from api.models.response import IngestResponse
from core.pdf_loader import extract_text_from_pdf
from core.web_scraper import scrape_url
from core.rss_poller import fetch_feed_entries
from config import MAX_UPLOAD_MB

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory source store: source_id → {raw_content, source_type, source_identifier, industry}
_source_store: dict[str, dict] = {}


def _new_source_id() -> str:
    return str(uuid.uuid4())


def _preview(text: str, n: int = 200) -> str:
    return text[:n].replace("\n", " ") + ("..." if len(text) > n else "")


def store_source(raw_content: str, source_type: str, source_identifier: str, industry: str) -> str:
    source_id = _new_source_id()
    _source_store[source_id] = {
        "raw_content": raw_content,
        "source_type": source_type,
        "source_identifier": source_identifier,
        "industry": industry,
    }
    return source_id


def get_source(source_id: str) -> dict | None:
    return _source_store.get(source_id)


@router.post("/ingest/pdf", response_model=IngestResponse)
async def ingest_pdf(
    file: UploadFile = File(...),
    industry: str = Form("auto"),
):
    """Upload a PDF file for regulatory analysis."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {MAX_UPLOAD_MB}MB limit",
        )

    try:
        text = extract_text_from_pdf(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not text.strip():
        raise HTTPException(status_code=422, detail="No text extracted from PDF")

    # Store bytes as latin-1 string for later retrieval
    source_id = store_source(
        raw_content=file_bytes.decode("latin-1"),
        source_type="pdf",
        source_identifier=file.filename,
        industry=industry,
    )
    # Also store the pre-extracted text to avoid double-parsing
    _source_store[source_id]["_parsed_text"] = text

    return IngestResponse(
        source_id=source_id,
        source_type="pdf",
        source_identifier=file.filename,
        char_count=len(text),
        preview=_preview(text),
        industry_hint=industry,
    )


@router.post("/ingest/url", response_model=IngestResponse)
async def ingest_url(req: URLIngestRequest):
    """Fetch and ingest a URL for regulatory analysis."""
    url_str = str(req.url)
    try:
        text = await scrape_url(url_str)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not text.strip():
        raise HTTPException(status_code=422, detail="No text extracted from URL")

    source_id = store_source(
        raw_content=url_str,
        source_type="url",
        source_identifier=url_str,
        industry=req.industry,
    )
    _source_store[source_id]["_parsed_text"] = text

    return IngestResponse(
        source_id=source_id,
        source_type="url",
        source_identifier=url_str,
        char_count=len(text),
        preview=_preview(text),
        industry_hint=req.industry,
    )


@router.post("/ingest/text", response_model=IngestResponse)
async def ingest_text(req: TextIngestRequest):
    """Ingest plain text for regulatory analysis."""
    # Normalize whitespace
    text = re.sub(r"\s+", " ", req.content.strip())

    source_id = store_source(
        raw_content=text,
        source_type="text",
        source_identifier=req.title,
        industry=req.industry,
    )
    _source_store[source_id]["_parsed_text"] = text

    return IngestResponse(
        source_id=source_id,
        source_type="text",
        source_identifier=req.title,
        char_count=len(text),
        preview=_preview(text),
        industry_hint=req.industry,
    )


@router.post("/ingest/rss", response_model=list[IngestResponse])
async def ingest_rss(req: RSSIngestRequest):
    """Poll an RSS feed and ingest entries for analysis."""
    feed_url = str(req.feed_url)
    try:
        entries = fetch_feed_entries(feed_url, max_entries=req.max_entries)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not entries:
        raise HTTPException(status_code=404, detail="No entries found in feed")

    responses = []
    for entry in entries:
        text = entry["full_text"]
        if not text.strip():
            continue
        source_id = store_source(
            raw_content=text,
            source_type="text",
            source_identifier=entry["title"] or feed_url,
            industry=req.industry,
        )
        _source_store[source_id]["_parsed_text"] = text
        responses.append(IngestResponse(
            source_id=source_id,
            source_type="rss",
            source_identifier=entry["title"] or feed_url,
            char_count=len(text),
            preview=_preview(text),
            industry_hint=req.industry,
        ))

    return responses
