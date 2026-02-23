from typing import TypedDict


class SimulationScenario(TypedDict):
    scenario_id: str          # "S001"–"S004"
    name: str                 # "Bull Case"|"Base Case"|"Bear Case"|"Tail Risk"
    probability: float        # 0.0–1.0; all 4 sum to 1.0
    macro_conditions: str
    competitive_conditions: str
    internal_conditions: str
    key_assumptions: list     # 3–5 items


class OutcomeProjection(TypedDict):
    scenario_id: str
    revenue_impact_pct: float   # point estimate
    revenue_impact_low: float   # range low
    revenue_impact_high: float  # range high
    cost_impact_pct: float
    success_probability: float  # 0.0–1.0
    roi_estimate: float         # %
    payback_months: int         # None allowed
    npv_qualitative: str        # "positive"|"negative"|"neutral"|"uncertain"
    key_drivers: list           # 2–4 items


class RiskFactor(TypedDict):
    risk_id: str              # "R001"...
    category: str             # from RISK_CATEGORIES
    name: str
    description: str
    likelihood: float         # 0.0–1.0
    impact: float             # 0.0–1.0
    risk_score: float         # likelihood × impact (computed in Python, not LLM)
    affected_scenarios: list
    mitigation: str


class StrategicSimulationState(TypedDict):
    # Input
    decision_text: str
    decision_title: str
    industry_context: str
    time_horizon: str           # "short_term"|"medium_term"|"long_term"
    # Node 1 outputs
    decision_type: str          # None allowed
    decision_domain: str        # None allowed
    key_decision_parameters: list
    decision_framing: str       # None allowed
    # Node 2 outputs
    scenarios: list
    # Node 3 outputs
    outcome_projections: list
    expected_value_pct: float   # None allowed
    expected_roi: float         # None allowed
    # Node 4 outputs
    risk_factors: list
    overall_risk_score: float   # None allowed
    risk_category_scores: dict
    # Node 5 outputs
    simulation_report_markdown: str   # None allowed
    strategic_recommendation: str    # None allowed
    confidence_level: str            # None allowed
    # Progress tracking
    current_agent: str
    progress_messages: list
    error: str                        # None allowed
