import json
import logging
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.models.request import AnalysisRequest
from api.models.response import (
    AnalysisResponse,
    ExtractedClauseResponse,
    ImpactScoreResponse,
    ActionItemResponse,
)
from api.routes.ingest import get_source
from agents.graph import run_analysis
from agents.state import RegulatoryAnalysisState
from agents.document_parser import parse_document
from agents.clause_extractor import extract_clauses
from agents.industry_classifier import classify_industry
from agents.impact_assessor import assess_impact
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)

router = APIRouter()


def _state_to_response(state: RegulatoryAnalysisState) -> AnalysisResponse:
    clauses = [
        ExtractedClauseResponse(
            clause_id=c["clause_id"],
            clause_type=c["clause_type"],
            raw_text=c["raw_text"],
            section_reference=c["section_reference"],
            keywords=c["keywords"],
        )
        for c in state.get("extracted_clauses", [])
    ]
    scores = [
        ImpactScoreResponse(
            clause_id=s["clause_id"],
            severity=s["severity"],
            severity_score=s["severity_score"],
            affected_functions=s["affected_functions"],
            compliance_deadline=s.get("compliance_deadline"),
            reasoning=s["reasoning"],
        )
        for s in state.get("impact_scores", [])
    ]
    actions = [
        ActionItemResponse(
            action_id=a["action_id"],
            clause_id=a["clause_id"],
            priority=a["priority"],
            responsible_function=a["responsible_function"],
            description=a["description"],
            estimated_effort=a["estimated_effort"],
            dependencies=a["dependencies"],
        )
        for a in state.get("action_items", [])
    ]
    impact = state.get("impact_scores", [])
    return AnalysisResponse(
        source_type=state["source_type"],
        source_identifier=state["source_identifier"],
        industry=state.get("detected_industry") or state["industry"],
        sub_domain=state.get("detected_sub_domain"),
        industry_confidence=state.get("industry_confidence"),
        regulation_name=state.get("regulation_name"),
        issuing_body=state.get("issuing_body"),
        effective_date=state.get("effective_date"),
        jurisdiction=state.get("jurisdiction"),
        extracted_clauses=clauses,
        impact_scores=scores,
        action_items=actions,
        action_plan_markdown=state.get("action_plan_markdown") or "",
        critical_count=sum(1 for s in impact if s["severity"] == "critical"),
        high_count=sum(1 for s in impact if s["severity"] == "high"),
        medium_count=sum(1 for s in impact if s["severity"] == "medium"),
        low_count=sum(1 for s in impact if s["severity"] == "low"),
        total_clauses=len(clauses),
        progress_messages=state.get("progress_messages", []),
        error=state.get("error"),
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _resolve_source(req: AnalysisRequest) -> tuple[str, str, str, str]:
    """Returns (source_type, raw_content, source_identifier, industry)."""
    if req.source_id:
        source = get_source(req.source_id)
        if not source:
            raise HTTPException(status_code=404, detail=f"Source ID '{req.source_id}' not found")
        industry = req.industry if req.industry != "auto" else source["industry"]
        # If pre-parsed text is cached (PDF/URL ingest), pass as "text" to avoid re-parsing
        if source.get("_parsed_text"):
            return ("text", source["_parsed_text"], source["source_identifier"], industry)
        return (
            source["source_type"],
            source["raw_content"],
            source["source_identifier"],
            industry,
        )
    return (
        req.source_type or "text",
        req.raw_content or "",
        req.source_identifier or "inline",
        req.industry,
    )


async def _stream_action_plan_tokens(prompt: str) -> AsyncGenerator[str, None]:
    """Stream action plan tokens from Ollama /api/chat directly."""
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


async def _analysis_stream(req: AnalysisRequest) -> AsyncGenerator[str, None]:
    """Full SSE stream: Nodes 1-4 sync, Node 5 action plan streamed token-by-token."""
    try:
        source_type, raw_content, source_identifier, industry = _resolve_source(req)
    except HTTPException as e:
        yield _sse({"event": "error", "message": e.detail})
        return

    # --- Node 1: Document Parser ---
    yield _sse({
        "event": "agent_start",
        "agent": "document_parser",
        "message": f"Parsing {source_type} input...",
    })

    state: RegulatoryAnalysisState = {
        "source_type": source_type,
        "raw_content": raw_content,
        "source_identifier": source_identifier,
        "industry": industry,
        "parsed_text": None,
        "extracted_clauses": [],
        "detected_industry": None,
        "detected_sub_domain": None,
        "industry_confidence": None,
        "impact_scores": [],
        "action_items": [],
        "action_plan_markdown": None,
        "regulation_name": None,
        "issuing_body": None,
        "effective_date": None,
        "jurisdiction": None,
        "current_agent": "pending",
        "progress_messages": [],
        "error": None,
    }

    try:
        state = parse_document(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "document_parser"})
        return

    yield _sse({
        "event": "agent_complete",
        "agent": "document_parser",
        "char_count": len(state.get("parsed_text") or ""),
        "regulation_name": state.get("regulation_name"),
        "issuing_body": state.get("issuing_body"),
    })

    # --- Node 2: Clause Extractor ---
    yield _sse({
        "event": "agent_start",
        "agent": "clause_extractor",
        "message": "Extracting regulatory clauses...",
    })

    try:
        state = extract_clauses(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "clause_extractor"})
        return

    if not state.get("extracted_clauses"):
        yield _sse({
            "event": "error",
            "message": state.get("error") or "No clauses extracted",
            "agent": "clause_extractor",
        })
        return

    yield _sse({
        "event": "agent_complete",
        "agent": "clause_extractor",
        "total_clauses": len(state["extracted_clauses"]),
    })

    # --- Node 3: Industry Classifier ---
    yield _sse({
        "event": "agent_start",
        "agent": "industry_classifier",
        "message": "Classifying industry and sub-domain...",
    })

    try:
        state = classify_industry(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "industry_classifier"})
        return

    yield _sse({
        "event": "agent_complete",
        "agent": "industry_classifier",
        "industry": state.get("detected_industry"),
        "sub_domain": state.get("detected_sub_domain"),
        "confidence": state.get("industry_confidence"),
    })

    # --- Node 4: Impact Assessor ---
    yield _sse({
        "event": "agent_start",
        "agent": "impact_assessor",
        "message": "Assessing impact severity...",
    })

    try:
        state = assess_impact(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "impact_assessor"})
        return

    impact = state.get("impact_scores", [])
    yield _sse({
        "event": "agent_complete",
        "agent": "impact_assessor",
        "critical_count": sum(1 for s in impact if s["severity"] == "critical"),
        "high_count": sum(1 for s in impact if s["severity"] == "high"),
        "medium_count": sum(1 for s in impact if s["severity"] == "medium"),
        "low_count": sum(1 for s in impact if s["severity"] == "low"),
    })

    # --- Node 5: Action Plan Generator (streamed) ---
    yield _sse({
        "event": "agent_start",
        "agent": "action_plan_generator",
        "message": "Generating compliance action plan...",
    })

    # Build action items (structured part, non-streamed)
    from agents.action_plan_generator import (
        _build_clauses_summary, _build_impact_summary, _build_action_items
    )
    from core.templates.financial_services import get_fs_action_plan_template
    from core.templates.healthcare import get_hc_action_plan_template

    detected_industry = state.get("detected_industry") or "financial_services"
    sub_domain = state.get("detected_sub_domain") or "general"
    impact_scores = state.get("impact_scores", [])
    severity_counts = {k: sum(1 for s in impact_scores if s["severity"] == k)
                       for k in ("critical", "high", "medium", "low")}

    action_items = _build_action_items(state.get("extracted_clauses", []), impact_scores, detected_industry)
    state = {**state, "action_items": action_items}

    clauses_summary = _build_clauses_summary(state["extracted_clauses"], impact_scores)
    impact_summary = _build_impact_summary(impact_scores)

    template_kwargs = dict(
        regulation_name=state.get("regulation_name") or "",
        issuing_body=state.get("issuing_body") or "",
        effective_date=state.get("effective_date") or "",
        sub_domain=sub_domain,
        jurisdiction=state.get("jurisdiction") or "",
        clauses_summary=clauses_summary,
        impact_summary=impact_summary,
        critical_count=severity_counts["critical"],
        high_count=severity_counts["high"],
        medium_count=severity_counts["medium"],
        low_count=severity_counts["low"],
    )

    if detected_industry == "healthcare":
        prompt = get_hc_action_plan_template(**template_kwargs)
    else:
        prompt = get_fs_action_plan_template(**template_kwargs)

    full_plan = ""
    token_count = 0
    try:
        async for token in _stream_action_plan_tokens(prompt):
            full_plan += token
            token_count += 1
            yield _sse({"event": "token", "token": token})
    except Exception as e:
        logger.error(f"Action plan streaming failed: {e}")
        yield _sse({"event": "error", "message": str(e), "agent": "action_plan_generator"})
        return

    state = {**state, "action_plan_markdown": full_plan, "current_agent": "done"}

    result = _state_to_response(state)
    yield _sse({"event": "done", "result": result.model_dump()})


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_blocking(req: AnalysisRequest):
    """Blocking analysis — runs all 5 nodes and returns final result."""
    try:
        source_type, raw_content, source_identifier, industry = _resolve_source(req)
    except HTTPException:
        raise

    logger.info(f"Analysis request: source_type={source_type}, industry={industry}")
    try:
        state = run_analysis(source_type, raw_content, source_identifier, industry)
    except Exception as e:
        logger.error(f"Analysis pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if state.get("error") and not state.get("extracted_clauses"):
        raise HTTPException(status_code=422, detail=state["error"])

    return _state_to_response(state)


@router.post("/analyze/stream")
async def analyze_stream(req: AnalysisRequest):
    """SSE streaming analysis — streams node progress and action plan tokens."""
    logger.info(f"Stream analysis request: source_id={req.source_id}, industry={req.industry}")
    return StreamingResponse(
        _analysis_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
