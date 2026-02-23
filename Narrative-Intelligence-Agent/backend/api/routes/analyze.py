import json
import logging
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.models.request import AnalyzeRequest
from api.models.response import (
    AnalysisResponse, ArticleResponse, SentimentScoreResponse,
    NarrativeResponse, NarrativePatternResponse,
)
from api.routes.topics import get_topic
from agents.graph import run_analysis
from agents.state import NarrativeIntelligenceState
from agents.source_aggregator import source_aggregator
from agents.sentiment_analyzer import sentiment_analyzer
from agents.narrative_extractor import narrative_extractor
from agents.pattern_mapper import pattern_mapper
from agents.intelligence_reporter import _extract_key_insights
from core.templates.report_template import get_report_prompt
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)
router = APIRouter()


def _state_to_response(state: NarrativeIntelligenceState) -> AnalysisResponse:
    articles = [
        ArticleResponse(
            article_id=a["article_id"], source=a["source"], title=a["title"],
            url=a.get("url", ""), published_at=a.get("published_at", ""),
            source_type=a["source_type"], content_preview=a["content"][:200],
        )
        for a in state.get("articles", [])
    ]
    scores = [
        SentimentScoreResponse(
            article_id=s["article_id"], source=s["source"], sentiment=s["sentiment"],
            score=s["score"], intensity=s["intensity"],
            key_emotional_signals=s.get("key_emotional_signals", []),
        )
        for s in state.get("sentiment_scores", [])
    ]
    narratives = [
        NarrativeResponse(
            narrative_id=n["narrative_id"], title=n["title"], description=n["description"],
            narrative_type=n["narrative_type"], framing=n["framing"],
            supporting_articles=n.get("supporting_articles", []),
            key_claims=n.get("key_claims", []), key_actors=n.get("key_actors", []),
            momentum=n["momentum"], contradicts=n.get("contradicts", []),
        )
        for n in state.get("narratives", [])
    ]
    patterns = [
        NarrativePatternResponse(
            pattern_id=p["pattern_id"], pattern_type=p["pattern_type"],
            description=p["description"],
            involved_narratives=p.get("involved_narratives", []),
            involved_sources=p.get("involved_sources", []),
            strength=p["strength"],
        )
        for p in state.get("narrative_patterns", [])
    ]
    return AnalysisResponse(
        topic=state.get("topic", ""),
        query=state.get("query", ""),
        time_window=state.get("time_window", "7d"),
        article_count=state.get("article_count", 0),
        sources_found=state.get("sources_found", []),
        articles=articles,
        sentiment_scores=scores,
        overall_sentiment=state.get("overall_sentiment", "neutral"),
        overall_sentiment_score=state.get("overall_sentiment_score", 0.0),
        sentiment_distribution=state.get("sentiment_distribution", {}),
        sentiment_by_source=state.get("sentiment_by_source", {}),
        sentiment_shift_signal=state.get("sentiment_shift_signal", "stable"),
        narratives=narratives,
        dominant_narratives=state.get("dominant_narratives", []),
        contested_topics=state.get("contested_topics", []),
        narrative_patterns=patterns,
        narrative_map_summary=state.get("narrative_map_summary", ""),
        key_actors=state.get("key_actors", []),
        key_claims=state.get("key_claims", []),
        intelligence_report_markdown=state.get("intelligence_report_markdown", ""),
        key_insights=state.get("key_insights", []),
        progress_messages=state.get("progress_messages", []),
        error=state.get("error"),
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _resolve_request(req: AnalyzeRequest) -> tuple[str, str, list, str]:
    if req.topic_id:
        stored = get_topic(req.topic_id)
        if not stored:
            raise HTTPException(status_code=404, detail=f"Topic '{req.topic_id}' not found")
        sources = req.sources or [{"type": s["type"], "value": s["value"], "label": s.get("label", "")} for s in stored["sources"]]
        return stored["topic"], req.query or stored.get("query", ""), sources, req.time_window or stored["time_window"]
    return req.topic, req.query, [s.model_dump() for s in req.sources], req.time_window


async def _stream_report_tokens(prompt: str) -> AsyncGenerator[str, None]:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "options": {"temperature": LLM_TEMPERATURE},
    }
    try:
        async with httpx.AsyncClient(timeout=240.0) as client:
            async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/chat", json=payload) as resp:
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
        logger.error(f"Report streaming error: {e}")
        yield f"\n\n[Streaming error: {e}]"


async def _analysis_stream(req: AnalyzeRequest) -> AsyncGenerator[str, None]:
    try:
        topic, query, sources_input, time_window = _resolve_request(req)
    except HTTPException as e:
        yield _sse({"event": "error", "message": e.detail})
        return

    state: NarrativeIntelligenceState = {
        "topic": topic, "query": query, "sources_input": sources_input,
        "time_window": time_window,
        "articles": [], "article_count": 0, "sources_found": [],
        "sentiment_scores": [], "overall_sentiment": "neutral",
        "overall_sentiment_score": 0.0, "sentiment_distribution": {},
        "sentiment_by_source": {}, "sentiment_shift_signal": "stable",
        "narratives": [], "dominant_narratives": [], "contested_topics": [],
        "narrative_patterns": [], "narrative_map_summary": "",
        "key_actors": [], "key_claims": [],
        "intelligence_report_markdown": "", "key_insights": [],
        "current_agent": "pending", "progress_messages": [], "error": None,
    }

    # --- Node 1: Source Aggregator ---
    yield _sse({"event": "agent_start", "agent": "source_aggregator", "message": "Aggregating media sources..."})
    try:
        state = source_aggregator(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "source_aggregator"})
        return
    for a in state.get("articles", []):
        yield _sse({"event": "agent_update", "agent": "source_aggregator",
                    "article_id": a["article_id"], "title": a["title"][:60], "source": a["source"]})
    yield _sse({"event": "agent_complete", "agent": "source_aggregator",
                "article_count": state.get("article_count", 0),
                "sources_found": state.get("sources_found", [])})

    # --- Node 2: Sentiment Analyzer ---
    yield _sse({"event": "agent_start", "agent": "sentiment_analyzer", "message": "Analyzing sentiment..."})
    try:
        state = sentiment_analyzer(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "sentiment_analyzer"})
        return
    for s in state.get("sentiment_scores", []):
        yield _sse({"event": "agent_update", "agent": "sentiment_analyzer",
                    "article_id": s["article_id"], "sentiment": s["sentiment"], "score": s["score"]})
    yield _sse({"event": "agent_complete", "agent": "sentiment_analyzer",
                "overall_sentiment": state.get("overall_sentiment"),
                "overall_sentiment_score": state.get("overall_sentiment_score"),
                "shift_signal": state.get("sentiment_shift_signal"),
                "distribution": state.get("sentiment_distribution")})

    # --- Node 3: Narrative Extractor ---
    yield _sse({"event": "agent_start", "agent": "narrative_extractor", "message": "Extracting narratives..."})
    try:
        state = narrative_extractor(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "narrative_extractor"})
        return
    for n in state.get("narratives", []):
        yield _sse({"event": "agent_update", "agent": "narrative_extractor",
                    "narrative_id": n["narrative_id"], "title": n["title"],
                    "type": n["narrative_type"], "momentum": n["momentum"]})
    yield _sse({"event": "agent_complete", "agent": "narrative_extractor",
                "narrative_count": len(state.get("narratives", [])),
                "dominant_count": len(state.get("dominant_narratives", []))})

    # --- Node 4: Pattern Mapper ---
    yield _sse({"event": "agent_start", "agent": "pattern_mapper", "message": "Mapping narrative patterns..."})
    try:
        state = pattern_mapper(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "pattern_mapper"})
        return
    yield _sse({"event": "agent_complete", "agent": "pattern_mapper",
                "pattern_count": len(state.get("narrative_patterns", [])),
                "key_actors": state.get("key_actors", [])[:5]})

    # --- Node 5: Intelligence Reporter (streamed) ---
    yield _sse({"event": "agent_start", "agent": "intelligence_reporter",
                "message": "Generating intelligence brief..."})

    key_insights = _extract_key_insights(state)
    state = {**state, "key_insights": key_insights}

    prompt = get_report_prompt(state)
    full_report = ""
    try:
        async for token in _stream_report_tokens(prompt):
            full_report += token
            yield _sse({"event": "token", "token": token})
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "intelligence_reporter"})
        return

    state = {**state, "intelligence_report_markdown": full_report, "current_agent": "done"}
    result = _state_to_response(state)
    yield _sse({"event": "done", "result": result.model_dump()})


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_blocking(req: AnalyzeRequest):
    try:
        topic, query, sources_input, time_window = _resolve_request(req)
    except HTTPException:
        raise
    logger.info(f"Analysis request: {topic}")
    try:
        state = run_analysis(topic, query, sources_input, time_window)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return _state_to_response(state)


@router.post("/analyze/stream")
async def analyze_stream(req: AnalyzeRequest):
    logger.info(f"Stream request: {req.topic}")
    return StreamingResponse(
        _analysis_stream(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
