from pydantic import BaseModel


class IngestResponse(BaseModel):
    source_id: str
    source_type: str
    source_identifier: str
    char_count: int
    preview: str
    industry_hint: str


class ExtractedClauseResponse(BaseModel):
    clause_id: str
    clause_type: str
    raw_text: str
    section_reference: str
    keywords: list[str]


class ImpactScoreResponse(BaseModel):
    clause_id: str
    severity: str
    severity_score: float
    affected_functions: list[str]
    compliance_deadline: str | None
    reasoning: str


class ActionItemResponse(BaseModel):
    action_id: str
    clause_id: str
    priority: str
    responsible_function: str
    description: str
    estimated_effort: str
    dependencies: list[str]


class AnalysisResponse(BaseModel):
    source_type: str
    source_identifier: str
    industry: str
    sub_domain: str | None
    industry_confidence: float | None

    regulation_name: str | None
    issuing_body: str | None
    effective_date: str | None
    jurisdiction: str | None

    extracted_clauses: list[ExtractedClauseResponse]
    impact_scores: list[ImpactScoreResponse]
    action_items: list[ActionItemResponse]
    action_plan_markdown: str

    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total_clauses: int

    progress_messages: list[str]
    error: str | None


class FeedEntry(BaseModel):
    title: str
    link: str
    published: str
    summary: str
    content_preview: str


class FeedPollResponse(BaseModel):
    feed_title: str
    feed_url: str
    entry_count: int
    entries: list[FeedEntry]


class KnownFeed(BaseModel):
    name: str
    url: str
    industry: str
    issuing_body: str


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    model_available: bool
    available_models: list[str]
    version: str
    service: str
