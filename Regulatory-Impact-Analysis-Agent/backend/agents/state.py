from typing import TypedDict


class ExtractedClause(TypedDict):
    clause_id: str           # "C001", "C002", ...
    clause_type: str         # from CLAUSE_TYPES controlled vocabulary
    raw_text: str            # verbatim quote ≤300 chars
    section_reference: str   # "Section 4.2(b)", "Article 12", etc.
    keywords: list[str]


class ImpactScore(TypedDict):
    clause_id: str
    severity: str            # "critical" | "high" | "medium" | "low"
    severity_score: float    # 0.0–1.0
    affected_functions: list[str]
    compliance_deadline: str | None
    reasoning: str


class ActionItem(TypedDict):
    action_id: str           # "A001"
    clause_id: str
    priority: str            # "immediate" | "short_term" | "long_term"
    responsible_function: str
    description: str
    estimated_effort: str
    dependencies: list[str]


class RegulatoryAnalysisState(TypedDict):
    # Input
    source_type: str         # "pdf" | "url" | "text" | "rss"
    raw_content: str
    source_identifier: str
    industry: str            # "financial_services" | "healthcare" | "auto"

    # Node outputs
    parsed_text: str | None
    extracted_clauses: list[ExtractedClause]
    detected_industry: str | None
    detected_sub_domain: str | None
    industry_confidence: float | None
    impact_scores: list[ImpactScore]
    action_items: list[ActionItem]
    action_plan_markdown: str | None

    # Metadata (extracted by Node 1)
    regulation_name: str | None
    issuing_body: str | None
    effective_date: str | None
    jurisdiction: str | None

    # Progress tracking
    current_agent: str
    progress_messages: list[str]
    error: str | None
