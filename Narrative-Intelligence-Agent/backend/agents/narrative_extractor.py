import json
import logging
import re

from core.llm import get_llm
from agents.state import NarrativeIntelligenceState
from config import MAX_NARRATIVES, NARRATIVE_TYPES, FRAMING_TYPES

logger = logging.getLogger(__name__)


def _strip_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def narrative_extractor(state: NarrativeIntelligenceState) -> NarrativeIntelligenceState:
    logger.info("Node 3: narrative_extractor — identifying narrative patterns")
    messages = list(state.get("progress_messages", []))
    messages.append("Extracting narratives and themes...")

    articles = state.get("articles", [])
    topic = state.get("topic", "")
    overall_sentiment = state.get("overall_sentiment", "neutral")
    by_source = state.get("sentiment_by_source", {})

    if not articles:
        messages.append("No articles for narrative extraction")
        return {
            **state,
            "narratives": [],
            "dominant_narratives": [],
            "contested_topics": [],
            "current_agent": "narrative_extractor",
            "progress_messages": messages,
        }

    # Build article summaries with sentiment context
    articles_block = "\n\n".join(
        f"[{a['article_id']}] {a['source']} (sentiment: {by_source.get(a['source'], 0):+.2f})\n"
        f"Title: {a['title']}\n{a['content'][:400]}"
        for a in articles
    )

    prompt = f"""Analyze the following collection of articles about "{topic}" and identify distinct narratives.

Overall sentiment context: {overall_sentiment}

Articles:
{articles_block}

Identify up to {MAX_NARRATIVES} distinct narratives being promoted across these sources.
Return ONLY a JSON array:
[
  {{
    "title": "<short, specific narrative headline>",
    "description": "<2-3 sentence description of what this narrative claims and how it frames the topic>",
    "narrative_type": "<{' | '.join(NARRATIVE_TYPES)}>",
    "framing": "<{' | '.join(FRAMING_TYPES)}>",
    "supporting_articles": ["<article_id like A001>"],
    "key_claims": ["<specific claim 1>", "<specific claim 2>", "<specific claim 3>"],
    "key_actors": ["<named person, org, or entity>"],
    "momentum": <0.0–1.0, how strongly this narrative is trending>,
    "contradicts": []
  }}
]

Narrative type guide:
- dominant: widely repeated across most sources
- emerging: appearing in few sources but gaining traction
- fading: present but declining
- contested: actively disputed between sources
- fringe: minority view, limited coverage

Return valid JSON array only. No markdown."""

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        raw = _strip_fence(response.content)
        data = json.loads(raw)

        if not isinstance(data, list):
            raise ValueError("Expected JSON array")

        narratives = []
        for i, item in enumerate(data[:MAX_NARRATIVES]):
            if not isinstance(item, dict):
                continue
            ntype = item.get("narrative_type", "emerging")
            if ntype not in NARRATIVE_TYPES:
                ntype = "emerging"
            framing = item.get("framing", "neutral")
            if framing not in FRAMING_TYPES:
                framing = "neutral"

            claims = item.get("key_claims", [])
            actors = item.get("key_actors", [])
            sup    = item.get("supporting_articles", [])

            narratives.append({
                "narrative_id": f"N{i+1:03d}",
                "title": str(item.get("title", f"Narrative {i+1}")),
                "description": str(item.get("description", "")),
                "narrative_type": ntype,
                "framing": framing,
                "supporting_articles": [str(a) for a in (sup if isinstance(sup, list) else [])],
                "key_claims": [str(c) for c in (claims if isinstance(claims, list) else [])[:5]],
                "key_actors": [str(a) for a in (actors if isinstance(actors, list) else [])[:6]],
                "momentum": min(1.0, max(0.0, float(item.get("momentum", 0.5)))),
                "contradicts": [],
            })

        dominant_narratives = [n["narrative_id"] for n in narratives if n["narrative_type"] == "dominant"]

        # Identify contested topics from contested + highest-momentum conflicting narratives
        contested_topics = [
            n["title"] for n in narratives if n["narrative_type"] == "contested"
        ]

        messages.append(
            f"Identified {len(narratives)} narratives "
            f"({len(dominant_narratives)} dominant, {len(contested_topics)} contested)"
        )

        return {
            **state,
            "narratives": narratives,
            "dominant_narratives": dominant_narratives,
            "contested_topics": contested_topics,
            "current_agent": "narrative_extractor",
            "progress_messages": messages,
        }

    except Exception as e:
        logger.error(f"narrative_extractor failed: {e}")
        messages.append(f"Narrative extraction error: {e}")
        return {
            **state,
            "narratives": [],
            "dominant_narratives": [],
            "contested_topics": [],
            "current_agent": "narrative_extractor",
            "progress_messages": messages,
            "error": str(e),
        }
