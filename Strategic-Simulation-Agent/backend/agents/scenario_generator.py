import json
import logging
import re

from core.llm import get_llm
from agents.state import StrategicSimulationState

logger = logging.getLogger(__name__)

_SCENARIO_NAMES = ["Bull Case", "Base Case", "Bear Case", "Tail Risk"]
_SCENARIO_IDS   = ["S001", "S002", "S003", "S004"]


def _strip_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _normalize_probabilities(scenarios: list) -> list:
    total = sum(s.get("probability", 0.0) for s in scenarios)
    if total <= 0:
        default_probs = [0.20, 0.45, 0.25, 0.10]
        for i, s in enumerate(scenarios):
            s["probability"] = default_probs[i] if i < len(default_probs) else 0.10
        return scenarios
    for s in scenarios:
        s["probability"] = round(s.get("probability", 0.0) / total, 4)
    return scenarios


def scenario_generator(state: StrategicSimulationState) -> StrategicSimulationState:
    logger.info("Node 2: scenario_generator — generating 4 scenarios")
    messages = list(state.get("progress_messages", []))
    messages.append("Generating Bull / Base / Bear / Tail Risk scenarios...")

    decision_text = state["decision_text"]
    decision_title = state.get("decision_title", "")
    industry_context = state.get("industry_context", "")
    decision_framing = state.get("decision_framing", "")
    decision_type = state.get("decision_type", "")
    time_horizon = state.get("time_horizon", "medium_term")

    prompt = f"""Generate exactly 4 strategic scenarios for this business decision.

Decision: {decision_title}
Description: {decision_text}
Industry Context: {industry_context}
Decision Type: {decision_type}
Decision Framing: {decision_framing}
Time Horizon: {time_horizon}

Return ONLY a JSON array with exactly 4 scenario objects in this order:
1. Bull Case (optimistic), 2. Base Case (most likely), 3. Bear Case (pessimistic), 4. Tail Risk (extreme downside)

Each scenario object:
{{
  "name": "<Bull Case|Base Case|Bear Case|Tail Risk>",
  "probability": <0.0-1.0, all 4 must be between 0 and 1>,
  "macro_conditions": "<macroeconomic and market environment description>",
  "competitive_conditions": "<competitive landscape description>",
  "internal_conditions": "<internal capabilities and execution description>",
  "key_assumptions": ["<assumption 1>", "<assumption 2>", "<assumption 3>"]
}}

Typical probability distribution: Bull ~0.20, Base ~0.45, Bear ~0.25, Tail ~0.10
Probabilities do NOT need to sum to exactly 1.0 — they will be normalized.
Return only valid JSON array. No markdown, no explanation."""

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        raw = _strip_fence(response.content)
        data = json.loads(raw)

        if not isinstance(data, list):
            raise ValueError("Expected JSON array of scenarios")

        scenarios = []
        for i, item in enumerate(data[:4]):
            if not isinstance(item, dict):
                continue
            name = item.get("name", _SCENARIO_NAMES[i] if i < 4 else f"Scenario {i+1}")
            if name not in _SCENARIO_NAMES:
                name = _SCENARIO_NAMES[i] if i < 4 else name

            assumptions = item.get("key_assumptions", [])
            if not isinstance(assumptions, list):
                assumptions = []

            scenarios.append({
                "scenario_id": _SCENARIO_IDS[i] if i < 4 else f"S{i+1:03d}",
                "name": name,
                "probability": float(item.get("probability", 0.25)),
                "macro_conditions": str(item.get("macro_conditions", "")),
                "competitive_conditions": str(item.get("competitive_conditions", "")),
                "internal_conditions": str(item.get("internal_conditions", "")),
                "key_assumptions": [str(a) for a in assumptions[:5]],
            })

        # Pad to 4 if fewer returned
        while len(scenarios) < 4:
            idx = len(scenarios)
            scenarios.append({
                "scenario_id": _SCENARIO_IDS[idx],
                "name": _SCENARIO_NAMES[idx],
                "probability": 0.25,
                "macro_conditions": "Not specified",
                "competitive_conditions": "Not specified",
                "internal_conditions": "Not specified",
                "key_assumptions": ["Assumption not specified"],
            })

        scenarios = _normalize_probabilities(scenarios)

        prob_sum = sum(s["probability"] for s in scenarios)
        messages.append(
            f"Generated {len(scenarios)} scenarios: "
            + ", ".join(f"{s['name']} ({s['probability']:.0%})" for s in scenarios)
            + f" [sum={prob_sum:.3f}]"
        )

        return {
            **state,
            "scenarios": scenarios,
            "current_agent": "scenario_generator",
            "progress_messages": messages,
        }
    except Exception as e:
        logger.error(f"scenario_generator failed: {e}")
        messages.append(f"Scenario generation error: {e}")
        # Fallback scenarios
        fallback = [
            {"scenario_id": "S001", "name": "Bull Case", "probability": 0.20,
             "macro_conditions": "Favorable", "competitive_conditions": "Favorable",
             "internal_conditions": "Strong execution", "key_assumptions": ["Market grows"]},
            {"scenario_id": "S002", "name": "Base Case", "probability": 0.45,
             "macro_conditions": "Neutral", "competitive_conditions": "Competitive",
             "internal_conditions": "Average execution", "key_assumptions": ["Market stable"]},
            {"scenario_id": "S003", "name": "Bear Case", "probability": 0.25,
             "macro_conditions": "Challenging", "competitive_conditions": "Intense",
             "internal_conditions": "Execution issues", "key_assumptions": ["Market contracts"]},
            {"scenario_id": "S004", "name": "Tail Risk", "probability": 0.10,
             "macro_conditions": "Severe disruption", "competitive_conditions": "Disrupted",
             "internal_conditions": "Major failure", "key_assumptions": ["Black swan event"]},
        ]
        return {
            **state,
            "scenarios": fallback,
            "current_agent": "scenario_generator",
            "progress_messages": messages,
            "error": str(e),
        }
