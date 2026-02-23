import json
import logging
import re
from collections import defaultdict
from statistics import mean

from core.llm import get_llm
from agents.state import NarrativeIntelligenceState
from config import SENTIMENT_BATCH_SIZE, SENTIMENT_LABELS

logger = logging.getLogger(__name__)


def _strip_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _classify_shift(scores: list) -> str:
    if len(scores) < 3:
        return "stable"
    first_half  = mean(scores[:len(scores)//2])
    second_half = mean(scores[len(scores)//2:])
    delta = second_half - first_half
    if abs(delta) < 0.1:
        return "stable"
    if delta > 0.15:
        return "shifting_positive"
    if delta < -0.15:
        return "shifting_negative"
    return "volatile"


def sentiment_analyzer(state: NarrativeIntelligenceState) -> NarrativeIntelligenceState:
    logger.info("Node 2: sentiment_analyzer — scoring article sentiment")
    messages = list(state.get("progress_messages", []))
    messages.append("Analyzing sentiment across articles...")

    articles = state.get("articles", [])
    topic = state.get("topic", "")

    if not articles:
        messages.append("No articles to score")
        return {
            **state,
            "sentiment_scores": [],
            "overall_sentiment": "neutral",
            "overall_sentiment_score": 0.0,
            "sentiment_distribution": {},
            "sentiment_by_source": {},
            "sentiment_shift_signal": "stable",
            "current_agent": "sentiment_analyzer",
            "progress_messages": messages,
        }

    llm = get_llm()
    all_scores: list = []

    for batch_start in range(0, len(articles), SENTIMENT_BATCH_SIZE):
        batch = articles[batch_start: batch_start + SENTIMENT_BATCH_SIZE]
        articles_block = "\n\n".join(
            f"[{a['article_id']}] Source: {a['source']}\nTitle: {a['title']}\n{a['content'][:500]}"
            for a in batch
        )

        prompt = f"""Analyze the sentiment of each article below regarding the topic: "{topic}".

{articles_block}

Return ONLY a JSON array — one object per article, in the same order:
[
  {{
    "article_id": "<e.g. A001>",
    "sentiment": "<positive|negative|neutral|mixed>",
    "score": <-1.0 to +1.0>,
    "intensity": "<strong|moderate|mild>",
    "key_emotional_signals": ["<word or phrase>"],
    "topic_sentiments": {{"<subtopic>": <score>}}
  }}
]

Score guide: +1.0 = most positive, -1.0 = most negative, 0.0 = neutral.
Return valid JSON array only. No markdown."""

        try:
            response = llm.invoke(prompt)
            raw = _strip_fence(response.content)
            data = json.loads(raw)
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    sentiment = item.get("sentiment", "neutral")
                    if sentiment not in SENTIMENT_LABELS:
                        sentiment = "neutral"
                    signals = item.get("key_emotional_signals", [])
                    if not isinstance(signals, list):
                        signals = []

                    # Find source for this article_id
                    aid = item.get("article_id", "")
                    src = next((a["source"] for a in batch if a["article_id"] == aid), "unknown")

                    all_scores.append({
                        "article_id": aid,
                        "source": src,
                        "sentiment": sentiment,
                        "score": max(-1.0, min(1.0, float(item.get("score", 0.0)))),
                        "intensity": item.get("intensity", "moderate"),
                        "key_emotional_signals": [str(s) for s in signals[:6]],
                        "topic_sentiments": item.get("topic_sentiments", {}),
                    })
        except Exception as e:
            logger.warning(f"Sentiment batch failed (articles {batch_start}–{batch_start+SENTIMENT_BATCH_SIZE}): {e}")
            # Fallback: neutral for each article in batch
            for a in batch:
                all_scores.append({
                    "article_id": a["article_id"],
                    "source": a["source"],
                    "sentiment": "neutral",
                    "score": 0.0,
                    "intensity": "mild",
                    "key_emotional_signals": [],
                    "topic_sentiments": {},
                })

    # Pure Python aggregations
    if all_scores:
        numeric_scores = [s["score"] for s in all_scores]
        overall_score = round(mean(numeric_scores), 4)
        overall_sentiment = (
            "positive" if overall_score > 0.15
            else "negative" if overall_score < -0.15
            else "neutral"
        )

        from collections import Counter
        cat_counts = Counter(s["sentiment"] for s in all_scores)
        total = len(all_scores)
        distribution = {cat: round(count / total, 3) for cat, count in cat_counts.items()}

        source_map: dict = defaultdict(list)
        for s in all_scores:
            source_map[s["source"]].append(s["score"])
        by_source = {src: round(mean(scores), 4) for src, scores in source_map.items()}

        shift_signal = _classify_shift(numeric_scores)
    else:
        overall_score = 0.0
        overall_sentiment = "neutral"
        distribution = {}
        by_source = {}
        shift_signal = "stable"

    messages.append(
        f"Sentiment scored: overall={overall_sentiment} ({overall_score:+.2f}), "
        f"signal={shift_signal}, distribution={distribution}"
    )

    return {
        **state,
        "sentiment_scores": all_scores,
        "overall_sentiment": overall_sentiment,
        "overall_sentiment_score": overall_score,
        "sentiment_distribution": distribution,
        "sentiment_by_source": by_source,
        "sentiment_shift_signal": shift_signal,
        "current_agent": "sentiment_analyzer",
        "progress_messages": messages,
    }
