from pydantic import BaseModel, field_validator


class SimulationRequest(BaseModel):
    decision_text: str
    decision_title: str
    industry_context: str = ""
    time_horizon: str = "medium_term"
    decision_id: str | None = None

    @field_validator("decision_text")
    @classmethod
    def validate_decision_text(cls, v: str) -> str:
        if len(v.strip()) < 20:
            raise ValueError("decision_text must be at least 20 characters")
        return v.strip()

    @field_validator("time_horizon")
    @classmethod
    def validate_time_horizon(cls, v: str) -> str:
        allowed = {"short_term", "medium_term", "long_term"}
        if v not in allowed:
            raise ValueError(f"time_horizon must be one of: {', '.join(allowed)}")
        return v


class DecisionStoreRequest(BaseModel):
    decision_text: str
    decision_title: str
    industry_context: str = ""
    time_horizon: str = "medium_term"
