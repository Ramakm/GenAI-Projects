import logging

from langgraph.graph import StateGraph, END

from agents.state import NarrativeIntelligenceState
from agents.source_aggregator import source_aggregator
from agents.sentiment_analyzer import sentiment_analyzer
from agents.narrative_extractor import narrative_extractor
from agents.pattern_mapper import pattern_mapper
from agents.intelligence_reporter import intelligence_reporter

logger = logging.getLogger(__name__)


def _build_graph():
    g = StateGraph(NarrativeIntelligenceState)
    g.add_node("source_aggregator",    source_aggregator)
    g.add_node("sentiment_analyzer",   sentiment_analyzer)
    g.add_node("narrative_extractor",  narrative_extractor)
    g.add_node("pattern_mapper",       pattern_mapper)
    g.add_node("intelligence_reporter", intelligence_reporter)

    g.set_entry_point("source_aggregator")
    g.add_edge("source_aggregator",    "sentiment_analyzer")
    g.add_edge("sentiment_analyzer",   "narrative_extractor")
    g.add_edge("narrative_extractor",  "pattern_mapper")
    g.add_edge("pattern_mapper",       "intelligence_reporter")
    g.add_edge("intelligence_reporter", END)

    return g.compile()


_compiled = _build_graph()


def run_analysis(
    topic: str,
    query: str,
    sources_input: list,
    time_window: str = "7d",
) -> NarrativeIntelligenceState:
    initial: NarrativeIntelligenceState = {
        "topic": topic,
        "query": query,
        "sources_input": sources_input,
        "time_window": time_window,
        "articles": [],
        "article_count": 0,
        "sources_found": [],
        "sentiment_scores": [],
        "overall_sentiment": "neutral",
        "overall_sentiment_score": 0.0,
        "sentiment_distribution": {},
        "sentiment_by_source": {},
        "sentiment_shift_signal": "stable",
        "narratives": [],
        "dominant_narratives": [],
        "contested_topics": [],
        "narrative_patterns": [],
        "narrative_map_summary": "",
        "key_actors": [],
        "key_claims": [],
        "intelligence_report_markdown": "",
        "key_insights": [],
        "current_agent": "pending",
        "progress_messages": [],
        "error": None,
    }
    logger.info(f"Starting narrative analysis for: {topic}")
    return _compiled.invoke(initial)
