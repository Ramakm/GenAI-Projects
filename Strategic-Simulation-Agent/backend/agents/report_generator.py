import logging
from statistics import stdev

from core.llm import get_llm
from core.templates.report_template import get_simulation_report_prompt
from agents.state import StrategicSimulationState

logger = logging.getLogger(__name__)


def _compute_recommendation(ev: float, overall_risk: float) -> str:
    if ev > 10.0 and overall_risk < 0.4:
        return "proceed"
    if ev > 0.0 and overall_risk < 0.6:
        return "proceed_with_caution"
    if ev > 0.0 and overall_risk >= 0.6:
        return "defer"
    return "do_not_proceed"


def _compute_confidence(scenarios: list) -> str:
    if len(scenarios) < 2:
        return "medium"
    probs = [s["probability"] for s in scenarios]
    try:
        std = stdev(probs)
    except Exception:
        return "medium"
    if std < 0.10:
        return "high"
    if std > 0.18:
        return "low"
    return "medium"


def report_generator(state: StrategicSimulationState) -> StrategicSimulationState:
    logger.info("Node 5: report_generator — generating strategic report")
    messages = list(state.get("progress_messages", []))
    messages.append("Generating strategic simulation report...")

    prompt = get_simulation_report_prompt(state)

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        report_markdown = response.content

        ev = state.get("expected_value_pct") or 0.0
        overall_risk = state.get("overall_risk_score") or 0.0
        recommendation = _compute_recommendation(ev, overall_risk)
        confidence = _compute_confidence(state.get("scenarios", []))

        messages.append(
            f"Report generated. Recommendation: {recommendation}, Confidence: {confidence}"
        )

        return {
            **state,
            "simulation_report_markdown": report_markdown,
            "strategic_recommendation": recommendation,
            "confidence_level": confidence,
            "current_agent": "done",
            "progress_messages": messages,
        }
    except Exception as e:
        logger.error(f"report_generator failed: {e}")
        messages.append(f"Report generation error: {e}")

        ev = state.get("expected_value_pct") or 0.0
        overall_risk = state.get("overall_risk_score") or 0.0
        recommendation = _compute_recommendation(ev, overall_risk)
        confidence = _compute_confidence(state.get("scenarios", []))

        return {
            **state,
            "simulation_report_markdown": f"# Report generation failed\n\n{e}",
            "strategic_recommendation": recommendation,
            "confidence_level": confidence,
            "current_agent": "done",
            "progress_messages": messages,
            "error": str(e),
        }
