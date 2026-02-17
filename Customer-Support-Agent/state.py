"""State definition for the customer support agent graph."""

from typing import Annotated, Optional

from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State that flows through the LangGraph agent."""

    customer_query: str
    category: Optional[str]
    sentiment: Optional[str]
    sentiment_score: Optional[float]
    is_escalated: bool
    response: Optional[str]
    escalation_reason: Optional[str]
