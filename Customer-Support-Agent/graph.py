"""LangGraph workflow definition for the customer support agent."""

import logging

from langgraph.graph import END, StateGraph

from nodes import (
    analyze_sentiment,
    categorize_query,
    check_escalation,
    escalate_to_human,
    generate_response,
)
from state import AgentState

logger = logging.getLogger(__name__)


def route_after_escalation_check(state: AgentState) -> str:
    """Route to escalation or normal response based on state."""
    if state.get("is_escalated"):
        return "escalate"
    return "respond"


def build_graph() -> StateGraph:
    """Build and compile the customer support agent graph.

    Flow:
        categorize_query -> analyze_sentiment -> check_escalation
            -> (escalated) -> escalate_to_human -> END
            -> (not escalated) -> generate_response -> END
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("categorize", categorize_query)
    workflow.add_node("analyze_sentiment", analyze_sentiment)
    workflow.add_node("check_escalation", check_escalation)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("escalate_to_human", escalate_to_human)

    # Define edges
    workflow.set_entry_point("categorize")
    workflow.add_edge("categorize", "analyze_sentiment")
    workflow.add_edge("analyze_sentiment", "check_escalation")

    # Conditional routing after escalation check
    workflow.add_conditional_edges(
        "check_escalation",
        route_after_escalation_check,
        {
            "escalate": "escalate_to_human",
            "respond": "generate_response",
        },
    )

    workflow.add_edge("generate_response", END)
    workflow.add_edge("escalate_to_human", END)

    return workflow.compile()


# Pre-built graph instance
agent = build_graph()
