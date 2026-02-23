import json
import logging
import re

from core.llm import get_llm
from agents.state import StrategicSimulationState
from config import DECISION_TYPES

logger = logging.getLogger(__name__)

_FALLBACK_TYPE = "market_entry"


def _strip_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def decision_framer(state: StrategicSimulationState) -> StrategicSimulationState:
    logger.info("Node 1: decision_framer — framing strategic decision")
    messages = list(state.get("progress_messages", []))
    messages.append("Framing decision and extracting parameters...")

    decision_text = state["decision_text"]
    industry_context = state.get("industry_context", "")
    time_horizon = state.get("time_horizon", "medium_term")

    prompt = f"""Analyze this strategic business decision and extract structured information.

Decision: {decision_text}
Industry Context: {industry_context}
Time Horizon: {time_horizon}

Return ONLY a JSON object with these exact fields:
{{
  "decision_type": "<one of: {', '.join(DECISION_TYPES)}>",
  "decision_domain": "<free-text domain, e.g. 'SaaS / Enterprise Software / European Market'>",
  "key_decision_parameters": ["<parameter 1>", "<parameter 2>", "<parameter 3>", "<parameter 4>"],
  "decision_framing": "<2-3 sentence strategic framing of the decision, its context, and what success looks like>"
}}

Return only valid JSON. No markdown, no explanation."""

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        raw = _strip_fence(response.content)
        data = json.loads(raw)

        decision_type = data.get("decision_type", _FALLBACK_TYPE)
        if decision_type not in DECISION_TYPES:
            decision_type = _FALLBACK_TYPE

        parameters = data.get("key_decision_parameters", [])
        if not isinstance(parameters, list):
            parameters = []

        messages.append(f"Decision classified as: {decision_type}")

        return {
            **state,
            "decision_type": decision_type,
            "decision_domain": data.get("decision_domain", ""),
            "key_decision_parameters": parameters[:6],
            "decision_framing": data.get("decision_framing", ""),
            "current_agent": "decision_framer",
            "progress_messages": messages,
        }
    except Exception as e:
        logger.error(f"decision_framer failed: {e}")
        messages.append(f"Decision framing error: {e}")
        return {
            **state,
            "decision_type": _FALLBACK_TYPE,
            "decision_domain": "",
            "key_decision_parameters": [],
            "decision_framing": "",
            "current_agent": "decision_framer",
            "progress_messages": messages,
            "error": str(e),
        }
