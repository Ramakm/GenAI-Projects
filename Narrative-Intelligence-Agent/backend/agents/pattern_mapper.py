import json
import logging
import re
from collections import Counter

from core.llm import get_llm
from agents.state import NarrativeIntelligenceState
from config import MAX_PATTERNS, PATTERN_TYPES

logger = logging.getLogger(__name__)


def _strip_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_global_actors_claims(narratives: list) -> tuple[list, list]:
    actor_counter: Counter = Counter()
    claim_counter: Counter = Counter()
    for n in narratives:
        for a in n.get("key_actors", []):
            actor_counter[a] += 1
        for c in n.get("key_claims", []):
            claim_counter[c] += 1
    top_actors  = [a for a, _ in actor_counter.most_common(10)]
    top_claims  = [c for c, _ in claim_counter.most_common(5)]
    return top_actors, top_claims


def pattern_mapper(state: NarrativeIntelligenceState) -> NarrativeIntelligenceState:
    logger.info("Node 4: pattern_mapper — mapping narrative interaction patterns")
    messages = list(state.get("progress_messages", []))
    messages.append("Mapping narrative patterns...")

    narratives = state.get("narratives", [])
    topic = state.get("topic", "")
    overall_sentiment = state.get("overall_sentiment", "neutral")
    overall_score = state.get("overall_sentiment_score", 0.0)
    by_source = state.get("sentiment_by_source", {})
    shift_signal = state.get("sentiment_shift_signal", "stable")

    if not narratives:
        messages.append("No narratives to map")
        return {
            **state,
            "narrative_patterns": [],
            "narrative_map_summary": "No narratives identified.",
            "key_actors": [],
            "key_claims": [],
            "current_agent": "pattern_mapper",
            "progress_messages": messages,
        }

    narrative_block = "\n".join(
        f"- [{n['narrative_id']}] {n['title']} ({n['narrative_type']}, momentum={n['momentum']:.0%}, framing={n['framing']})"
        for n in narratives
    )
    source_block = "\n".join(
        f"- {src}: {score:+.2f}" for src, score in sorted(by_source.items(), key=lambda x: -x[1])[:8]
    )

    prompt = f"""Analyze how the following narratives interact and identify meta-patterns.

Topic: {topic}
Overall Sentiment: {overall_sentiment} ({overall_score:+.2f}), Signal: {shift_signal}

Narratives:
{narrative_block}

Sentiment by Source:
{source_block}

Return a JSON object with these fields:
{{
  "patterns": [
    {{
      "pattern_type": "<{' | '.join(PATTERN_TYPES)}>",
      "description": "<2-3 sentence description of this pattern and its significance>",
      "involved_narratives": ["<narrative title>"],
      "involved_sources": ["<source name>"],
      "strength": <0.0–1.0>
    }}
  ],
  "narrative_map_summary": "<3-4 sentence overview of the complete narrative landscape — what is dominant, what is contested, what is emerging, and what the overall media ecosystem looks like>",
  "key_actors": ["<most cross-narrative actor>"],
  "key_claims": ["<most repeated or contested claim>"]
}}

Pattern type guide:
- convergence: multiple sources aligning on same narrative
- divergence: sources actively contradicting each other
- amplification: a narrative rapidly gaining cross-source traction
- suppression: a narrative being systematically underrepresented
- reversal: sentiment on a topic changing direction
- echo_chamber: same narrative repeated with no counter-narrative

Return up to {MAX_PATTERNS} patterns. Return valid JSON object only."""

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        raw = _strip_fence(response.content)
        data = json.loads(raw)

        raw_patterns = data.get("patterns", []) if isinstance(data, dict) else []
        map_summary  = data.get("narrative_map_summary", "") if isinstance(data, dict) else ""
        key_actors   = data.get("key_actors", []) if isinstance(data, dict) else []
        key_claims   = data.get("key_claims", []) if isinstance(data, dict) else []

        patterns = []
        for i, p in enumerate(raw_patterns[:MAX_PATTERNS]):
            if not isinstance(p, dict):
                continue
            ptype = p.get("pattern_type", "convergence")
            if ptype not in PATTERN_TYPES:
                ptype = "convergence"
            inv_n = p.get("involved_narratives", [])
            inv_s = p.get("involved_sources", [])
            patterns.append({
                "pattern_id": f"P{i+1:03d}",
                "pattern_type": ptype,
                "description": str(p.get("description", "")),
                "involved_narratives": [str(x) for x in (inv_n if isinstance(inv_n, list) else [])],
                "involved_sources": [str(x) for x in (inv_s if isinstance(inv_s, list) else [])],
                "strength": min(1.0, max(0.0, float(p.get("strength", 0.5)))),
            })

        # Fall back to pure-Python actor/claim extraction if LLM didn't provide
        if not key_actors or not key_claims:
            pa, pc = _extract_global_actors_claims(narratives)
            key_actors = key_actors or pa
            key_claims = key_claims or pc

        messages.append(
            f"Mapped {len(patterns)} patterns. "
            f"Key actors: {', '.join(key_actors[:4])}."
        )

        return {
            **state,
            "narrative_patterns": patterns,
            "narrative_map_summary": str(map_summary),
            "key_actors": [str(a) for a in key_actors[:10]],
            "key_claims": [str(c) for c in key_claims[:5]],
            "current_agent": "pattern_mapper",
            "progress_messages": messages,
        }

    except Exception as e:
        logger.error(f"pattern_mapper failed: {e}")
        messages.append(f"Pattern mapping error: {e}")
        pa, pc = _extract_global_actors_claims(narratives)
        return {
            **state,
            "narrative_patterns": [],
            "narrative_map_summary": "Pattern mapping failed.",
            "key_actors": pa,
            "key_claims": pc,
            "current_agent": "pattern_mapper",
            "progress_messages": messages,
            "error": str(e),
        }
