import json
import logging
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.models.request import SimulationRequest
from api.models.response import (
    SimulationResponse,
    ScenarioResponse,
    OutcomeProjectionResponse,
    RiskFactorResponse,
)
from api.routes.decisions import get_decision
from agents.graph import run_simulation
from agents.state import StrategicSimulationState
from agents.decision_framer import decision_framer
from agents.scenario_generator import scenario_generator
from agents.outcome_simulator import outcome_simulator
from agents.risk_analyzer import risk_analyzer
from agents.report_generator import _compute_recommendation, _compute_confidence
from core.templates.report_template import get_simulation_report_prompt
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)
router = APIRouter()


def _state_to_response(state: StrategicSimulationState) -> SimulationResponse:
    scenarios = [
        ScenarioResponse(
            scenario_id=s["scenario_id"],
            name=s["name"],
            probability=s["probability"],
            macro_conditions=s["macro_conditions"],
            competitive_conditions=s["competitive_conditions"],
            internal_conditions=s["internal_conditions"],
            key_assumptions=s["key_assumptions"],
        )
        for s in state.get("scenarios", [])
    ]
    projections = [
        OutcomeProjectionResponse(
            scenario_id=o["scenario_id"],
            revenue_impact_pct=o["revenue_impact_pct"],
            revenue_impact_low=o["revenue_impact_low"],
            revenue_impact_high=o["revenue_impact_high"],
            cost_impact_pct=o["cost_impact_pct"],
            success_probability=o["success_probability"],
            roi_estimate=o["roi_estimate"],
            payback_months=o.get("payback_months"),
            npv_qualitative=o["npv_qualitative"],
            key_drivers=o["key_drivers"],
        )
        for o in state.get("outcome_projections", [])
    ]
    risks = [
        RiskFactorResponse(
            risk_id=r["risk_id"],
            category=r["category"],
            name=r["name"],
            description=r["description"],
            likelihood=r["likelihood"],
            impact=r["impact"],
            risk_score=r["risk_score"],
            affected_scenarios=r["affected_scenarios"],
            mitigation=r["mitigation"],
        )
        for r in state.get("risk_factors", [])
    ]
    return SimulationResponse(
        decision_title=state.get("decision_title", ""),
        decision_type=state.get("decision_type"),
        decision_domain=state.get("decision_domain"),
        key_decision_parameters=state.get("key_decision_parameters", []),
        decision_framing=state.get("decision_framing"),
        time_horizon=state.get("time_horizon", "medium_term"),
        industry_context=state.get("industry_context", ""),
        scenarios=scenarios,
        outcome_projections=projections,
        expected_value_pct=state.get("expected_value_pct"),
        expected_roi=state.get("expected_roi"),
        risk_factors=risks,
        overall_risk_score=state.get("overall_risk_score"),
        risk_category_scores=state.get("risk_category_scores", {}),
        simulation_report_markdown=state.get("simulation_report_markdown"),
        strategic_recommendation=state.get("strategic_recommendation"),
        confidence_level=state.get("confidence_level"),
        progress_messages=state.get("progress_messages", []),
        error=state.get("error"),
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _resolve_request(req: SimulationRequest) -> tuple[str, str, str, str]:
    """Returns (decision_text, decision_title, industry_context, time_horizon)."""
    if req.decision_id:
        stored = get_decision(req.decision_id)
        if not stored:
            raise HTTPException(status_code=404, detail=f"Decision ID '{req.decision_id}' not found")
        return (
            stored["decision_text"],
            stored["decision_title"],
            req.industry_context or stored.get("industry_context", ""),
            req.time_horizon or stored.get("time_horizon", "medium_term"),
        )
    return req.decision_text, req.decision_title, req.industry_context, req.time_horizon


async def _stream_report_tokens(prompt: str) -> AsyncGenerator[str, None]:
    """Stream report tokens from Ollama /api/chat directly."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "options": {"temperature": LLM_TEMPERATURE},
    }
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
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
        logger.error(f"Report streaming error: {e}")
        yield f"\n\n[Streaming error: {e}]"


async def _simulation_stream(req: SimulationRequest) -> AsyncGenerator[str, None]:
    """Full SSE stream: Nodes 1-4 sync, Node 5 report streamed token-by-token."""
    try:
        decision_text, decision_title, industry_context, time_horizon = _resolve_request(req)
    except HTTPException as e:
        yield _sse({"event": "error", "message": e.detail})
        return

    state: StrategicSimulationState = {
        "decision_text": decision_text,
        "decision_title": decision_title,
        "industry_context": industry_context,
        "time_horizon": time_horizon,
        "decision_type": None,
        "decision_domain": None,
        "key_decision_parameters": [],
        "decision_framing": None,
        "scenarios": [],
        "outcome_projections": [],
        "expected_value_pct": None,
        "expected_roi": None,
        "risk_factors": [],
        "overall_risk_score": None,
        "risk_category_scores": {},
        "simulation_report_markdown": None,
        "strategic_recommendation": None,
        "confidence_level": None,
        "current_agent": "pending",
        "progress_messages": [],
        "error": None,
    }

    # --- Node 1: Decision Framer ---
    yield _sse({"event": "agent_start", "agent": "decision_framer", "message": "Framing decision..."})
    try:
        state = decision_framer(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "decision_framer"})
        return
    yield _sse({
        "event": "agent_complete",
        "agent": "decision_framer",
        "decision_type": state.get("decision_type"),
        "decision_domain": state.get("decision_domain"),
    })

    # --- Node 2: Scenario Generator ---
    yield _sse({"event": "agent_start", "agent": "scenario_generator", "message": "Generating 4 scenarios..."})
    try:
        state = scenario_generator(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "scenario_generator"})
        return
    yield _sse({
        "event": "agent_complete",
        "agent": "scenario_generator",
        "scenarios": [{"name": s["name"], "probability": s["probability"]} for s in state.get("scenarios", [])],
    })

    # --- Node 3: Outcome Simulator ---
    yield _sse({"event": "agent_start", "agent": "outcome_simulator", "message": "Simulating outcomes per scenario..."})
    try:
        state = outcome_simulator(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "outcome_simulator"})
        return
    for o in state.get("outcome_projections", []):
        yield _sse({
            "event": "agent_update",
            "agent": "outcome_simulator",
            "scenario_id": o["scenario_id"],
            "revenue_impact_pct": o["revenue_impact_pct"],
            "success_probability": o["success_probability"],
        })
    yield _sse({
        "event": "agent_complete",
        "agent": "outcome_simulator",
        "expected_value_pct": state.get("expected_value_pct"),
        "expected_roi": state.get("expected_roi"),
    })

    # --- Node 4: Risk Analyzer ---
    yield _sse({"event": "agent_start", "agent": "risk_analyzer", "message": "Analyzing risk factors..."})
    try:
        state = risk_analyzer(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "risk_analyzer"})
        return
    for r in state.get("risk_factors", []):
        yield _sse({
            "event": "agent_update",
            "agent": "risk_analyzer",
            "risk_id": r["risk_id"],
            "name": r["name"],
            "risk_score": r["risk_score"],
        })
    yield _sse({
        "event": "agent_complete",
        "agent": "risk_analyzer",
        "overall_risk_score": state.get("overall_risk_score"),
        "risk_count": len(state.get("risk_factors", [])),
    })

    # --- Node 5: Report Generator (streamed) ---
    yield _sse({"event": "agent_start", "agent": "report_generator", "message": "Generating strategic report..."})

    prompt = get_simulation_report_prompt(state)
    full_report = ""
    try:
        async for token in _stream_report_tokens(prompt):
            full_report += token
            yield _sse({"event": "token", "token": token})
    except Exception as e:
        logger.error(f"Report streaming failed: {e}")
        yield _sse({"event": "error", "message": str(e), "agent": "report_generator"})
        return

    ev = state.get("expected_value_pct") or 0.0
    overall_risk = state.get("overall_risk_score") or 0.0
    recommendation = _compute_recommendation(ev, overall_risk)
    confidence = _compute_confidence(state.get("scenarios", []))

    state = {
        **state,
        "simulation_report_markdown": full_report,
        "strategic_recommendation": recommendation,
        "confidence_level": confidence,
        "current_agent": "done",
    }

    result = _state_to_response(state)
    yield _sse({"event": "done", "result": result.model_dump()})


@router.post("/simulate", response_model=SimulationResponse)
async def simulate_blocking(req: SimulationRequest):
    """Blocking simulation — runs all 5 nodes and returns final result."""
    try:
        decision_text, decision_title, industry_context, time_horizon = _resolve_request(req)
    except HTTPException:
        raise

    logger.info(f"Simulation request: {decision_title}")
    try:
        state = run_simulation(decision_text, decision_title, industry_context, time_horizon)
    except Exception as e:
        logger.error(f"Simulation pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return _state_to_response(state)


@router.post("/simulate/stream")
async def simulate_stream(req: SimulationRequest):
    """SSE streaming simulation — streams node progress and report tokens."""
    logger.info(f"Stream simulation request: {req.decision_title}")
    return StreamingResponse(
        _simulation_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
