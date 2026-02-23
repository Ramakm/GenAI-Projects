from typing import Optional
from pydantic import BaseModel


class ArticleResponse(BaseModel):
    article_id: str
    source: str
    title: str
    url: str
    published_at: str
    source_type: str
    content_preview: str


class SentimentScoreResponse(BaseModel):
    article_id: str
    source: str
    sentiment: str
    score: float
    intensity: str
    key_emotional_signals: list[str]


class NarrativeResponse(BaseModel):
    narrative_id: str
    title: str
    description: str
    narrative_type: str
    framing: str
    supporting_articles: list[str]
    key_claims: list[str]
    key_actors: list[str]
    momentum: float
    contradicts: list[str]


class NarrativePatternResponse(BaseModel):
    pattern_id: str
    pattern_type: str
    description: str
    involved_narratives: list[str]
    involved_sources: list[str]
    strength: float


class AnalysisResponse(BaseModel):
    topic: str
    query: str
    time_window: str
    article_count: int
    sources_found: list[str]
    articles: list[ArticleResponse]
    sentiment_scores: list[SentimentScoreResponse]
    overall_sentiment: str
    overall_sentiment_score: float
    sentiment_distribution: dict
    sentiment_by_source: dict
    sentiment_shift_signal: str
    narratives: list[NarrativeResponse]
    dominant_narratives: list[str]
    contested_topics: list[str]
    narrative_patterns: list[NarrativePatternResponse]
    narrative_map_summary: str
    key_actors: list[str]
    key_claims: list[str]
    intelligence_report_markdown: str
    key_insights: list[str]
    progress_messages: list[str]
    error: Optional[str]


class TopicStoreResponse(BaseModel):
    topic_id: str
    topic: str
    message: str


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    model_available: bool
    model: str
    version: str = "1.0.0"
