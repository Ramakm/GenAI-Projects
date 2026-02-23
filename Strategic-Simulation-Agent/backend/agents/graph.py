import logging

from langgraph.graph import StateGraph, END

from agents.state import StrategicSimulationState
from agents.decision_framer import decision_framer
from agents.scenario_generator import scenario_generator
from agents.outcome_simulator import outcome_simulator
from agents.risk_analyzer import risk_analyzer
from agents.report_generator import report_generator

logger = logging.getLogger(__name__)


def _build_graph() -> StateGraph:
    graph = StateGraph(StrategicSimulationState)
    graph.add_node("decision_framer", decision_framer)
    graph.add_node("scenario_generator", scenario_generator)
    graph.add_node("outcome_simulator", outcome_simulator)
    graph.add_node("risk_analyzer", risk_analyzer)
    graph.add_node("report_generator", report_generator)

    graph.set_entry_point("decision_framer")
    graph.add_edge("decision_framer", "scenario_generator")
    graph.add_edge("scenario_generator", "outcome_simulator")
    graph.add_edge("outcome_simulator", "risk_analyzer")
    graph.add_edge("risk_analyzer", "report_generator")
    graph.add_edge("report_generator", END)

    return graph.compile()


_compiled_graph = _build_graph()


def run_simulation(
    decision_text: str,
    decision_title: str,
    industry_context: str = "",
    time_horizon: str = "medium_term",
) -> StrategicSimulationState:
    initial_state: StrategicSimulationState = {
        "decision_text": decision_text,
        "decision_title": decision_title,
        "industry_context": industry_context,
        "time_horizon": time_horizon,
        "decision_type": None,
        "decision_domain": None,
        "key_decision_parameters": [],
        "decision_framing": None,
        "scenarios": [],
        "outcome_projections": [],
        "expected_value_pct": None,
        "expected_roi": None,
        "risk_factors": [],
        "overall_risk_score": None,
        "risk_category_scores": {},
        "simulation_report_markdown": None,
        "strategic_recommendation": None,
        "confidence_level": None,
        "current_agent": "pending",
        "progress_messages": [],
        "error": None,
    }
    logger.info(f"Starting simulation pipeline for: {decision_title}")
    result = _compiled_graph.invoke(initial_state)
    return result
