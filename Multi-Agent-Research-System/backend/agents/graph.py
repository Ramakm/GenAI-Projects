from typing import List

from langgraph.graph import StateGraph, END

from agents.state import ResearchState
from agents.source_gatherer import gather_sources
from agents.citation_verifier import verify_citations
from agents.report_writer import write_report

# Build the linear pipeline graph
workflow = StateGraph(ResearchState)

workflow.add_node("source_gatherer", gather_sources)
workflow.add_node("citation_verifier", verify_citations)
workflow.add_node("report_writer", write_report)

workflow.set_entry_point("source_gatherer")
workflow.add_edge("source_gatherer", "citation_verifier")
workflow.add_edge("citation_verifier", "report_writer")
workflow.add_edge("report_writer", END)

app_graph = workflow.compile()


def run_research(topic: str, urls: List[str]) -> ResearchState:
    """Run the full 3-agent research pipeline and return final state."""
    initial_state: ResearchState = {
        "topic": topic,
        "urls": urls,
        "sources": [],
        "failed_urls": [],
        "citations": [],
        "report_markdown": None,
        "overall_confidence": None,
        "current_agent": "pending",
        "progress_messages": [],
        "error": None,
    }
    return app_graph.invoke(initial_state)
