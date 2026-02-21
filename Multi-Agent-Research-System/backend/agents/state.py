from typing import List, Optional
from typing_extensions import TypedDict


class SourceInfo(TypedDict):
    url: str
    domain: str
    raw_text: str            # First 4000 chars of visible text
    key_claims: List[str]    # LLM-extracted (3-8 specific factual claims)
    fetch_error: Optional[str]  # None = success


class CitationResult(TypedDict):
    url: str
    domain: str
    key_claims: List[str]
    confidence_score: float       # 0.0–1.0 composite
    credibility_reasoning: str    # LLM free-text
    domain_score: float           # Rule-based: .edu/.gov=0.7, .org=0.6, else 0.4
    relevance_score: float        # LLM-assessed 0.0–1.0
    is_usable: bool               # confidence_score >= 0.3


class ResearchState(TypedDict):
    topic: str
    urls: List[str]
    sources: List[SourceInfo]
    failed_urls: List[str]
    citations: List[CitationResult]
    report_markdown: Optional[str]
    overall_confidence: Optional[float]
    current_agent: str            # for SSE progress
    progress_messages: List[str]  # append-only log
    error: Optional[str]
