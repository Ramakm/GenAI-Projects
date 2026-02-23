import logging
import uuid

import networkx as nx

from agents.state import KnowledgeGraphState
from core.graph_store import store_graph, get_graph_data

logger = logging.getLogger(__name__)


def _build_nx_graph(entities: list, relationships: list) -> nx.DiGraph:
    G = nx.DiGraph()
    for e in entities:
        G.add_node(
            e["entity_id"],
            name=e["name"],
            entity_type=e["entity_type"],
            description=e.get("description", ""),
            aliases=e.get("aliases", []),
            confidence=e.get("confidence", 0.8),
        )
    for r in relationships:
        src = r.get("source_entity_id", "")
        tgt = r.get("target_entity_id", "")
        if src and tgt and G.has_node(src) and G.has_node(tgt):
            G.add_edge(
                src, tgt,
                rel_id=r.get("rel_id", ""),
                relationship_type=r.get("relationship_type", "RELATED_TO"),
                description=r.get("description", ""),
                weight=r.get("weight", 0.5),
                source_name=r.get("source_name", ""),
                target_name=r.get("target_name", ""),
            )
    return G


def graph_builder(state: KnowledgeGraphState) -> KnowledgeGraphState:
    logger.info("Node 4: graph_builder — constructing NetworkX knowledge graph")
    messages = list(state.get("progress_messages", []))
    messages.append("Building knowledge graph...")

    entities = state.get("entities", [])
    relationships = state.get("relationships", [])

    if not entities:
        messages.append("No entities — returning empty graph")
        return {
            **state, "graph_id": "", "node_count": 0, "edge_count": 0,
            "graph_density": 0.0, "connected_components": 0, "central_entities": [],
            "current_agent": "graph_builder", "progress_messages": messages,
        }

    G = _build_nx_graph(entities, relationships)

    # Stats
    node_count = G.number_of_nodes()
    edge_count = G.number_of_edges()
    density = round(nx.density(G), 4)
    try:
        cc = nx.number_weakly_connected_components(G)
    except Exception:
        cc = 1

    # Top-5 nodes by degree centrality
    centrality = nx.degree_centrality(G)
    top_nodes = sorted(centrality, key=lambda n: centrality[n], reverse=True)[:5]
    central_entities = [G.nodes[n].get("name", n) for n in top_nodes]

    # Store
    graph_id = str(uuid.uuid4())[:8]
    store_graph(
        graph_id,
        G,
        {
            "document_title": state.get("document_title", ""),
            "domain": state.get("domain", ""),
            "node_count": node_count,
            "edge_count": edge_count,
            "graph_density": density,
            "connected_components": cc,
            "central_entities": central_entities,
            "entity_types_found": state.get("entity_types_found", []),
            "relationship_types_found": state.get("relationship_types_found", []),
            "entities": entities,
            "relationships": relationships,
        },
    )

    messages.append(
        f"Graph built: {node_count} nodes, {edge_count} edges, density={density:.4f}, "
        f"{cc} component(s). ID: {graph_id}"
    )

    return {
        **state,
        "graph_id": graph_id,
        "node_count": node_count,
        "edge_count": edge_count,
        "graph_density": density,
        "connected_components": cc,
        "central_entities": central_entities,
        "current_agent": "graph_builder",
        "progress_messages": messages,
    }
