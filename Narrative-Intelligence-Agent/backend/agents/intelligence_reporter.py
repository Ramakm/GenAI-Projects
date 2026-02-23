import json
import logging
import re

from core.llm import get_llm
from core.templates.report_template import get_report_prompt
from agents.state import NarrativeIntelligenceState

logger = logging.getLogger(__name__)


def _strip_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_key_insights(state: NarrativeIntelligenceState) -> list:
    """Generate 3-5 key insights via LLM using the accumulated state."""
    topic = state.get("topic", "")
    overall_sentiment = state.get("overall_sentiment", "neutral")
    overall_score = state.get("overall_sentiment_score", 0.0)
    shift_signal = state.get("sentiment_shift_signal", "stable")
    narratives = state.get("narratives", [])
    patterns = state.get("narrative_patterns", [])
    key_actors = state.get("key_actors", [])

    dominant = [n["title"] for n in narratives if n["narrative_type"] == "dominant"]
    emerging = [n["title"] for n in narratives if n["narrative_type"] == "emerging"]
    pattern_types = [p["pattern_type"] for p in patterns]

    prompt = f"""Generate 3-5 concise, actionable intelligence insights about the narrative landscape for "{topic}".

Sentiment: {overall_sentiment} ({overall_score:+.2f}), Signal: {shift_signal}
Dominant narratives: {', '.join(dominant[:3]) if dominant else 'none'}
Emerging narratives: {', '.join(emerging[:3]) if emerging else 'none'}
Patterns detected: {', '.join(pattern_types)}
Key actors: {', '.join(key_actors[:5])}

Return ONLY a JSON array of 3-5 insight strings:
["<insight 1>", "<insight 2>", ...]

Each insight should be 1-2 sentences, specific, and analytically meaningful. No generic statements."""

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        raw = _strip_fence(response.content)
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(i) for i in data[:5]]
    except Exception as e:
        logger.warning(f"Key insights extraction failed: {e}")

    # Fallback: construct from state
    insights = []
    if overall_score != 0:
        insights.append(
            f"Overall coverage sentiment is {overall_sentiment} ({overall_score:+.2f}), "
            f"with signal: {shift_signal.replace('_', ' ')}."
        )
    if dominant:
        insights.append(f"The dominant narrative is '{dominant[0]}'.")
    if emerging:
        insights.append(f"Watch emerging narrative: '{emerging[0]}'.")
    return insights or ["Insufficient data for key insights."]


def intelligence_reporter(state: NarrativeIntelligenceState) -> NarrativeIntelligenceState:
    logger.info("Node 5: intelligence_reporter — generating intelligence brief")
    messages = list(state.get("progress_messages", []))
    messages.append("Generating intelligence brief...")

    key_insights = _extract_key_insights(state)

    try:
        prompt = get_report_prompt(state)
        llm = get_llm()
        response = llm.invoke(prompt)
        report_markdown = response.content.strip()
        messages.append("Intelligence brief generated.")
        return {
            **state,
            "intelligence_report_markdown": report_markdown,
            "key_insights": key_insights,
            "current_agent": "done",
            "progress_messages": messages,
        }
    except Exception as e:
        logger.error(f"intelligence_reporter failed: {e}")
        messages.append(f"Report generation error: {e}")
        return {
            **state,
            "intelligence_report_markdown": f"# Report Generation Failed\n\n{e}",
            "key_insights": key_insights,
            "current_agent": "done",
            "progress_messages": messages,
            "error": str(e),
        }
