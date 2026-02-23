from langgraph.graph import StateGraph, END

from agents.state import RegulatoryAnalysisState
from agents.document_parser import parse_document
from agents.clause_extractor import extract_clauses
from agents.industry_classifier import classify_industry
from agents.impact_assessor import assess_impact
from agents.action_plan_generator import generate_action_plan


def _route_after_extraction(state: RegulatoryAnalysisState) -> str:
    if state.get("extracted_clauses"):
        return "industry_classifier"
    return END


workflow = StateGraph(RegulatoryAnalysisState)

workflow.add_node("document_parser",       parse_document)
workflow.add_node("clause_extractor",      extract_clauses)
workflow.add_node("industry_classifier",   classify_industry)
workflow.add_node("impact_assessor",       assess_impact)
workflow.add_node("action_plan_generator", generate_action_plan)

workflow.set_entry_point("document_parser")
workflow.add_edge("document_parser", "clause_extractor")
workflow.add_conditional_edges("clause_extractor", _route_after_extraction)
workflow.add_edge("industry_classifier", "impact_assessor")
workflow.add_edge("impact_assessor",     "action_plan_generator")
workflow.add_edge("action_plan_generator", END)

app_graph = workflow.compile()


def run_analysis(
    source_type: str,
    raw_content: str,
    source_identifier: str,
    industry: str,
) -> RegulatoryAnalysisState:
    """Run the full 5-node regulatory analysis pipeline and return final state."""
    initial_state: RegulatoryAnalysisState = {
        "source_type": source_type,
        "raw_content": raw_content,
        "source_identifier": source_identifier,
        "industry": industry,
        "parsed_text": None,
        "extracted_clauses": [],
        "detected_industry": None,
        "detected_sub_domain": None,
        "industry_confidence": None,
        "impact_scores": [],
        "action_items": [],
        "action_plan_markdown": None,
        "regulation_name": None,
        "issuing_body": None,
        "effective_date": None,
        "jurisdiction": None,
        "current_agent": "pending",
        "progress_messages": [],
        "error": None,
    }
    return app_graph.invoke(initial_state)
