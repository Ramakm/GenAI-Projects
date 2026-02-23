import json
import logging
import re

from core.llm import get_llm
from agents.state import StrategicSimulationState

logger = logging.getLogger(__name__)


def _strip_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def outcome_simulator(state: StrategicSimulationState) -> StrategicSimulationState:
    logger.info("Node 3: outcome_simulator — projecting outcomes per scenario")
    messages = list(state.get("progress_messages", []))
    messages.append("Simulating outcomes per scenario...")

    scenarios = state.get("scenarios", [])
    decision_text = state["decision_text"]
    decision_title = state.get("decision_title", "")
    industry_context = state.get("industry_context", "")
    decision_framing = state.get("decision_framing", "")
    time_horizon = state.get("time_horizon", "medium_term")

    scenarios_summary = "\n".join(
        f"- {s['scenario_id']} ({s['name']}, p={s['probability']:.2f}): "
        f"macro={s.get('macro_conditions','')[:80]}"
        for s in scenarios
    )

    prompt = f"""Project quantitative financial outcomes for each strategic scenario.

Decision: {decision_title}
Description: {decision_text}
Industry Context: {industry_context}
Decision Framing: {decision_framing}
Time Horizon: {time_horizon}

Scenarios:
{scenarios_summary}

Return ONLY a JSON array with one OutcomeProjection object per scenario (same order as above):
[
  {{
    "scenario_id": "<S001|S002|S003|S004>",
    "revenue_impact_pct": <point estimate % change, e.g. 15.0 or -8.0>,
    "revenue_impact_low": <low end of range, e.g. 5.0>,
    "revenue_impact_high": <high end of range, e.g. 30.0>,
    "cost_impact_pct": <% change in costs, positive = increase>,
    "success_probability": <0.0-1.0>,
    "roi_estimate": <% ROI>,
    "payback_months": <integer months or null>,
    "npv_qualitative": "<positive|negative|neutral|uncertain>",
    "key_drivers": ["<driver 1>", "<driver 2>", "<driver 3>"]
  }}
]

Use realistic estimates based on the scenario conditions. Bull=optimistic, Base=moderate, Bear=negative, Tail=severe.
Return only valid JSON array. No markdown, no explanation."""

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        raw = _strip_fence(response.content)
        data = json.loads(raw)

        if not isinstance(data, list):
            raise ValueError("Expected JSON array of outcome projections")

        projections = []
        for i, item in enumerate(data[:4]):
            if not isinstance(item, dict):
                continue
            drivers = item.get("key_drivers", [])
            if not isinstance(drivers, list):
                drivers = []
            payback = item.get("payback_months")
            if payback is not None:
                try:
                    payback = int(payback)
                except (ValueError, TypeError):
                    payback = None

            projections.append({
                "scenario_id": item.get("scenario_id", scenarios[i]["scenario_id"] if i < len(scenarios) else f"S{i+1:03d}"),
                "revenue_impact_pct": float(item.get("revenue_impact_pct", 0.0)),
                "revenue_impact_low": float(item.get("revenue_impact_low", 0.0)),
                "revenue_impact_high": float(item.get("revenue_impact_high", 0.0)),
                "cost_impact_pct": float(item.get("cost_impact_pct", 0.0)),
                "success_probability": float(item.get("success_probability", 0.5)),
                "roi_estimate": float(item.get("roi_estimate", 0.0)),
                "payback_months": payback,
                "npv_qualitative": str(item.get("npv_qualitative", "uncertain")),
                "key_drivers": [str(d) for d in drivers[:4]],
            })

        # Pad missing
        while len(projections) < len(scenarios):
            idx = len(projections)
            sid = scenarios[idx]["scenario_id"] if idx < len(scenarios) else f"S{idx+1:03d}"
            projections.append({
                "scenario_id": sid,
                "revenue_impact_pct": 0.0, "revenue_impact_low": -10.0, "revenue_impact_high": 10.0,
                "cost_impact_pct": 0.0, "success_probability": 0.5, "roi_estimate": 0.0,
                "payback_months": None, "npv_qualitative": "uncertain", "key_drivers": [],
            })

        # Pure Python: compute expected value
        proj_map = {p["scenario_id"]: p for p in projections}
        expected_value_pct = sum(
            s["probability"] * proj_map.get(s["scenario_id"], {}).get("revenue_impact_pct", 0.0)
            for s in scenarios
        )
        expected_roi = sum(
            s["probability"] * proj_map.get(s["scenario_id"], {}).get("roi_estimate", 0.0)
            for s in scenarios
        )

        messages.append(
            f"Outcomes simulated. EV={expected_value_pct:+.2f}%, Expected ROI={expected_roi:+.2f}%"
        )

        return {
            **state,
            "outcome_projections": projections,
            "expected_value_pct": round(expected_value_pct, 4),
            "expected_roi": round(expected_roi, 4),
            "current_agent": "outcome_simulator",
            "progress_messages": messages,
        }
    except Exception as e:
        logger.error(f"outcome_simulator failed: {e}")
        messages.append(f"Outcome simulation error: {e}")
        return {
            **state,
            "outcome_projections": [],
            "expected_value_pct": 0.0,
            "expected_roi": 0.0,
            "current_agent": "outcome_simulator",
            "progress_messages": messages,
            "error": str(e),
        }
