from typing import Optional
from pydantic import BaseModel


class ScenarioResponse(BaseModel):
    scenario_id: str
    name: str
    probability: float
    macro_conditions: str
    competitive_conditions: str
    internal_conditions: str
    key_assumptions: list[str]


class OutcomeProjectionResponse(BaseModel):
    scenario_id: str
    revenue_impact_pct: float
    revenue_impact_low: float
    revenue_impact_high: float
    cost_impact_pct: float
    success_probability: float
    roi_estimate: float
    payback_months: Optional[int]
    npv_qualitative: str
    key_drivers: list[str]


class RiskFactorResponse(BaseModel):
    risk_id: str
    category: str
    name: str
    description: str
    likelihood: float
    impact: float
    risk_score: float
    affected_scenarios: list[str]
    mitigation: str


class SimulationResponse(BaseModel):
    decision_title: str
    decision_type: Optional[str]
    decision_domain: Optional[str]
    key_decision_parameters: list[str]
    decision_framing: Optional[str]
    time_horizon: str
    industry_context: str
    scenarios: list[ScenarioResponse]
    outcome_projections: list[OutcomeProjectionResponse]
    expected_value_pct: Optional[float]
    expected_roi: Optional[float]
    risk_factors: list[RiskFactorResponse]
    overall_risk_score: Optional[float]
    risk_category_scores: dict
    simulation_report_markdown: Optional[str]
    strategic_recommendation: Optional[str]
    confidence_level: Optional[str]
    progress_messages: list[str]
    error: Optional[str]


class DecisionStoreResponse(BaseModel):
    decision_id: str
    decision_title: str
    decision_text: str
    industry_context: str
    time_horizon: str
    message: str


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    model_available: bool
    model: str
    version: str = "1.0.0"
