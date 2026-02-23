from typing import TypedDict


class Article(TypedDict):
    article_id: str       # "A001"…
    source: str           # domain / feed name
    title: str
    content: str          # cleaned, truncated
    url: str
    published_at: str     # ISO string or ""
    source_type: str      # "rss" | "url" | "text"


class SentimentScore(TypedDict):
    article_id: str
    source: str
    sentiment: str        # "positive"|"negative"|"neutral"|"mixed"
    score: float          # -1.0 to +1.0
    intensity: str        # "strong"|"moderate"|"mild"
    key_emotional_signals: list   # words/phrases driving the sentiment
    topic_sentiments: dict        # {"subtopic": score}


class Narrative(TypedDict):
    narrative_id: str     # "N001"…
    title: str
    description: str      # 2-3 sentences
    narrative_type: str   # dominant|emerging|fading|contested|fringe
    framing: str          # positive|negative|neutral|alarmist|optimistic
    supporting_articles: list   # article_ids
    key_claims: list      # 3-5 claims
    key_actors: list      # named actors/entities
    momentum: float       # 0.0–1.0
    contradicts: list     # narrative_ids this conflicts with


class NarrativePattern(TypedDict):
    pattern_id: str       # "P001"…
    pattern_type: str     # convergence|divergence|amplification|suppression|reversal|echo_chamber
    description: str
    involved_narratives: list   # narrative titles
    involved_sources: list
    strength: float       # 0.0–1.0


class NarrativeIntelligenceState(TypedDict):
    # Input
    topic: str
    query: str
    sources_input: list          # list of {type, value, label}
    time_window: str             # "24h"|"7d"|"30d"|"all"
    # Node 1 — Source Aggregator
    articles: list               # list[Article]
    article_count: int
    sources_found: list
    # Node 2 — Sentiment Analyzer
    sentiment_scores: list       # list[SentimentScore]
    overall_sentiment: str
    overall_sentiment_score: float
    sentiment_distribution: dict # {"positive": 0.3, "negative": 0.5, ...}
    sentiment_by_source: dict    # {source: avg_score}
    sentiment_shift_signal: str  # "stable"|"shifting_positive"|"shifting_negative"|"volatile"
    # Node 3 — Narrative Extractor
    narratives: list             # list[Narrative]
    dominant_narratives: list    # narrative_ids of dominant type
    contested_topics: list       # topics with conflicting narratives
    # Node 4 — Pattern Mapper
    narrative_patterns: list     # list[NarrativePattern]
    narrative_map_summary: str
    key_actors: list
    key_claims: list
    # Node 5 — Intelligence Reporter
    intelligence_report_markdown: str
    key_insights: list           # 3-5 bullet strings
    # Progress
    current_agent: str
    progress_messages: list
    error: str
