from typing import List, Optional
from pydantic import BaseModel


class CitationResponse(BaseModel):
    url: str
    domain: str
    key_claims: List[str]
    confidence_score: float
    credibility_reasoning: str
    domain_score: float
    relevance_score: float
    is_usable: bool


class ResearchResponse(BaseModel):
    topic: str
    report_markdown: str
    overall_confidence: float
    citations: List[CitationResponse]
    failed_urls: List[str]
    progress_messages: List[str]
    sources_ok: int
    sources_failed: int


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    model_available: bool
    available_models: List[str]
    version: str = "1.0.0"
