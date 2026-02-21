import json
import logging
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, LLM_TEMPERATURE, MAX_TEXT_CHARS
from api.models.request import ResearchRequest
from api.models.response import ResearchResponse, CitationResponse
from agents.graph import run_research
from agents.state import ResearchState, CitationResult

logger = logging.getLogger(__name__)

router = APIRouter()


def _state_to_response(state: ResearchState) -> ResearchResponse:
    """Convert final ResearchState to Pydantic response model."""
    citations = [
        CitationResponse(
            url=c["url"],
            domain=c["domain"],
            key_claims=c["key_claims"],
            confidence_score=c["confidence_score"],
            credibility_reasoning=c["credibility_reasoning"],
            domain_score=c["domain_score"],
            relevance_score=c["relevance_score"],
            is_usable=c["is_usable"],
        )
        for c in state.get("citations", [])
    ]
    return ResearchResponse(
        topic=state["topic"],
        report_markdown=state.get("report_markdown") or "",
        overall_confidence=state.get("overall_confidence") or 0.0,
        citations=citations,
        failed_urls=state.get("failed_urls", []),
        progress_messages=state.get("progress_messages", []),
        sources_ok=sum(1 for s in state.get("sources", []) if s["fetch_error"] is None),
        sources_failed=len(state.get("failed_urls", [])),
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def _stream_report_tokens(topic: str, prompt: str) -> AsyncGenerator[str, None]:
    """Stream report tokens from Ollama HTTP API directly."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "options": {"temperature": LLM_TEMPERATURE},
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"\n\n[Streaming error: {e}]"


async def _research_stream(req: ResearchRequest) -> AsyncGenerator[str, None]:
    """Full SSE stream: agents 1&2 sync, agent 3 streamed tokens."""
    topic = req.topic
    urls = req.urls

    # --- Agent 1: Source Gatherer ---
    yield _sse({
        "event": "agent_start",
        "agent": "source_gatherer",
        "message": f"Fetching {len(urls)} URL(s)...",
    })

    from agents.source_gatherer import gather_sources
    from agents.state import ResearchState as RS

    state: RS = {
        "topic": topic,
        "urls": urls,
        "sources": [],
        "failed_urls": [],
        "citations": [],
        "report_markdown": None,
        "overall_confidence": None,
        "current_agent": "pending",
        "progress_messages": [],
        "error": None,
    }

    try:
        state = gather_sources(state)
    except Exception as e:
        logger.error(f"source_gatherer failed: {e}")
        yield _sse({"event": "error", "message": str(e), "agent": "source_gatherer"})
        return

    # Replay progress messages from gatherer
    for msg in state["progress_messages"]:
        if "FAILED:" in msg:
            url_part = msg.split("FAILED:")[-1].strip().split(" —")[0].strip()
            err_part = msg.split("—")[-1].strip() if "—" in msg else ""
            yield _sse({
                "event": "agent_update",
                "agent": "source_gatherer",
                "url": url_part,
                "message": msg,
            })
        elif "Fetched:" in msg:
            yield _sse({
                "event": "agent_update",
                "agent": "source_gatherer",
                "message": msg,
            })

    yield _sse({
        "event": "agent_complete",
        "agent": "source_gatherer",
        "sources_ok": len(urls) - len(state["failed_urls"]),
        "sources_failed": len(state["failed_urls"]),
    })

    # --- Agent 2: Citation Verifier ---
    usable_sources = [s for s in state["sources"] if s["fetch_error"] is None]
    yield _sse({
        "event": "agent_start",
        "agent": "citation_verifier",
        "message": f"Verifying {len(usable_sources)} source(s)...",
    })

    from agents.citation_verifier import verify_citations
    try:
        state = verify_citations(state)
    except Exception as e:
        logger.error(f"citation_verifier failed: {e}")
        yield _sse({"event": "error", "message": str(e), "agent": "citation_verifier"})
        return

    for c in state["citations"]:
        yield _sse({
            "event": "agent_update",
            "agent": "citation_verifier",
            "url": c["url"],
            "confidence": c["confidence_score"],
            "is_usable": c["is_usable"],
        })

    usable_citations = [c for c in state["citations"] if c["is_usable"]]
    avg_conf = (
        sum(c["confidence_score"] for c in usable_citations) / len(usable_citations)
        if usable_citations else 0.0
    )
    yield _sse({
        "event": "agent_complete",
        "agent": "citation_verifier",
        "avg_confidence": round(avg_conf, 4),
    })

    # --- Agent 3: Report Writer (streamed) ---
    yield _sse({
        "event": "agent_start",
        "agent": "report_writer",
        "message": "Writing research report...",
    })

    # Build the same prompt as report_writer.py but stream tokens
    from agents.report_writer import _build_citation_context, _compute_overall_confidence
    overall_confidence = _compute_overall_confidence(state["citations"])
    citation_context = _build_citation_context(state["citations"])
    total_count = len(state["citations"])
    usable_count = len(usable_citations)

    table_rows = []
    for i, c in enumerate(state["citations"], 1):
        status = "✓ Usable" if c["is_usable"] else "✗ Low-confidence"
        table_rows.append(
            f"| {i} | {c['domain']} | {c['confidence_score']:.2f} | {status} |"
        )
    table_str = "\n".join(table_rows)

    report_prompt = (
        f"You are writing a professional research report.\n\n"
        f"Research topic: {topic}\n"
        f"Overall confidence score: {overall_confidence:.2f}/1.0\n"
        f"Sources analyzed: {total_count} total, {usable_count} usable\n\n"
        f"Sources and claims:\n{citation_context}\n\n"
        f"Write a structured Markdown research report with exactly these sections:\n\n"
        f"# Research Report: {topic}\n\n"
        f"**Overall Confidence: {overall_confidence:.1f}/1.0** | "
        f"**Sources: {usable_count}/{total_count} usable**\n\n"
        f"## Executive Summary\n"
        f"## Key Findings\n"
        f"## Detailed Analysis\n"
        f"## Source Assessment\n"
        f"| # | Domain | Confidence | Status |\n"
        f"|---|--------|------------|--------|\n"
        f"{table_str}\n\n"
        f"## References\n\n"
        f"Use ONLY information from the provided sources. "
        f"Cite sources inline with [N] notation."
    )

    full_report = ""
    try:
        async for token in _stream_report_tokens(topic, report_prompt):
            full_report += token
            yield _sse({"event": "token", "token": token})
    except Exception as e:
        logger.error(f"report_writer streaming failed: {e}")
        yield _sse({"event": "error", "message": str(e), "agent": "report_writer"})
        return

    full_report += "\n\n---\n*Generated by Multi-Agent Research System*"

    # Build final response
    state["report_markdown"] = full_report
    state["overall_confidence"] = overall_confidence
    state["current_agent"] = "done"

    result = _state_to_response(state)
    yield _sse({"event": "done", "result": result.model_dump()})


@router.post("/research", response_model=ResearchResponse)
async def research_blocking(req: ResearchRequest):
    """Blocking research endpoint — runs all 3 agents and returns final report."""
    logger.info(f"Research request: topic='{req.topic}', urls={req.urls}")
    try:
        state = run_research(req.topic, req.urls)
    except Exception as e:
        logger.error(f"Research pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if state.get("error"):
        raise HTTPException(status_code=500, detail=state["error"])

    return _state_to_response(state)


@router.post("/research/stream")
async def research_stream(req: ResearchRequest):
    """SSE streaming research endpoint."""
    logger.info(f"Stream research request: topic='{req.topic}', urls={req.urls}")
    return StreamingResponse(
        _research_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
