import logging

from langgraph.graph import StateGraph, END

from agents.state import KnowledgeGraphState
from agents.document_ingester import document_ingester
from agents.entity_extractor import entity_extractor
from agents.relationship_extractor import relationship_extractor
from agents.graph_builder import graph_builder
from agents.graph_summarizer import graph_summarizer

logger = logging.getLogger(__name__)


def _build_graph() -> StateGraph:
    g = StateGraph(KnowledgeGraphState)
    g.add_node("document_ingester", document_ingester)
    g.add_node("entity_extractor", entity_extractor)
    g.add_node("relationship_extractor", relationship_extractor)
    g.add_node("graph_builder", graph_builder)
    g.add_node("graph_summarizer", graph_summarizer)

    g.set_entry_point("document_ingester")
    g.add_edge("document_ingester", "entity_extractor")
    g.add_edge("entity_extractor", "relationship_extractor")
    g.add_edge("relationship_extractor", "graph_builder")
    g.add_edge("graph_builder", "graph_summarizer")
    g.add_edge("graph_summarizer", END)

    return g.compile()


_compiled = _build_graph()


def run_pipeline(
    raw_content: str,
    document_title: str,
    domain: str = "",
    source_type: str = "text",
    source_identifier: str = "inline",
) -> KnowledgeGraphState:
    initial: KnowledgeGraphState = {
        "raw_content": raw_content,
        "document_title": document_title,
        "domain": domain,
        "source_type": source_type,
        "source_identifier": source_identifier,
        "parsed_text": "",
        "text_chunks": [],
        "char_count": 0,
        "entities": [],
        "entity_types_found": [],
        "relationships": [],
        "relationship_types_found": [],
        "graph_id": "",
        "node_count": 0,
        "edge_count": 0,
        "graph_density": 0.0,
        "connected_components": 0,
        "central_entities": [],
        "graph_summary": "",
        "current_agent": "pending",
        "progress_messages": [],
        "error": None,
    }
    logger.info(f"Starting pipeline for: {document_title}")
    return _compiled.invoke(initial)
