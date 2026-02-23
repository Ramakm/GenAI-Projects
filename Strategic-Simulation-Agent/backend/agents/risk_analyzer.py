import json
import logging
import re
from statistics import mean

from core.llm import get_llm
from agents.state import StrategicSimulationState
from config import RISK_CATEGORIES, MAX_RISKS

logger = logging.getLogger(__name__)


def _strip_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def risk_analyzer(state: StrategicSimulationState) -> StrategicSimulationState:
    logger.info("Node 4: risk_analyzer — identifying and scoring risk factors")
    messages = list(state.get("progress_messages", []))
    messages.append("Analyzing risk factors across 5 categories...")

    decision_text = state["decision_text"]
    decision_title = state.get("decision_title", "")
    industry_context = state.get("industry_context", "")
    scenarios = state.get("scenarios", [])
    decision_type = state.get("decision_type", "")
    time_horizon = state.get("time_horizon", "medium_term")

    scenario_names = [s["name"] for s in scenarios]
    scenarios_summary = "\n".join(
        f"- {s['name']} (p={s['probability']:.2f})" for s in scenarios
    )

    prompt = f"""Identify and assess risk factors for this strategic decision.

Decision: {decision_title}
Description: {decision_text}
Industry Context: {industry_context}
Decision Type: {decision_type}
Time Horizon: {time_horizon}

Scenarios: {', '.join(scenario_names)}

Return ONLY a JSON array of risk factors (up to {MAX_RISKS}), covering all 5 categories: {', '.join(RISK_CATEGORIES)}.

Each risk factor:
{{
  "category": "<market|operational|financial|strategic|regulatory>",
  "name": "<short risk name>",
  "description": "<1-2 sentence description>",
  "likelihood": <0.0-1.0>,
  "impact": <0.0-1.0>,
  "affected_scenarios": ["<Bull Case|Base Case|Bear Case|Tail Risk>"],
  "mitigation": "<1 sentence mitigation strategy>"
}}

Do NOT compute risk_score — it will be calculated in Python.
Return only valid JSON array. No markdown, no explanation."""

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        raw = _strip_fence(response.content)
        data = json.loads(raw)

        if not isinstance(data, list):
            raise ValueError("Expected JSON array of risk factors")

        risk_factors = []
        for i, item in enumerate(data[:MAX_RISKS]):
            if not isinstance(item, dict):
                continue
            category = item.get("category", "market")
            if category not in RISK_CATEGORIES:
                category = "market"

            affected = item.get("affected_scenarios", [])
            if not isinstance(affected, list):
                affected = []

            likelihood = min(1.0, max(0.0, float(item.get("likelihood", 0.5))))
            impact = min(1.0, max(0.0, float(item.get("impact", 0.5))))
            risk_score = round(likelihood * impact, 4)  # Pure Python, not LLM

            risk_factors.append({
                "risk_id": f"R{i+1:03d}",
                "category": category,
                "name": str(item.get("name", f"Risk {i+1}")),
                "description": str(item.get("description", "")),
                "likelihood": likelihood,
                "impact": impact,
                "risk_score": risk_score,
                "affected_scenarios": [str(a) for a in affected],
                "mitigation": str(item.get("mitigation", "")),
            })

        # Pure Python aggregations
        if risk_factors:
            overall_risk_score = round(mean(r["risk_score"] for r in risk_factors), 4)
            risk_category_scores = {}
            for cat in RISK_CATEGORIES:
                cat_scores = [r["risk_score"] for r in risk_factors if r["category"] == cat]
                risk_category_scores[cat] = round(mean(cat_scores), 4) if cat_scores else 0.0
        else:
            overall_risk_score = 0.0
            risk_category_scores = {cat: 0.0 for cat in RISK_CATEGORIES}

        messages.append(
            f"Identified {len(risk_factors)} risks. Overall risk score: {overall_risk_score:.2f}"
        )

        return {
            **state,
            "risk_factors": risk_factors,
            "overall_risk_score": overall_risk_score,
            "risk_category_scores": risk_category_scores,
            "current_agent": "risk_analyzer",
            "progress_messages": messages,
        }
    except Exception as e:
        logger.error(f"risk_analyzer failed: {e}")
        messages.append(f"Risk analysis error: {e}")
        return {
            **state,
            "risk_factors": [],
            "overall_risk_score": 0.0,
            "risk_category_scores": {cat: 0.0 for cat in RISK_CATEGORIES},
            "current_agent": "risk_analyzer",
            "progress_messages": messages,
            "error": str(e),
        }
