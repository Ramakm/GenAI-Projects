import logging
from typing import Optional

import networkx as nx

logger = logging.getLogger(__name__)

# In-memory stores — keyed by graph_id
_graphs: dict[str, nx.DiGraph] = {}
_graph_data: dict[str, dict] = {}


def store_graph(graph_id: str, G: nx.DiGraph, data: dict) -> None:
    _graphs[graph_id] = G
    _graph_data[graph_id] = data
    logger.info(f"Stored graph '{graph_id}': {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")


def get_graph(graph_id: str) -> Optional[nx.DiGraph]:
    return _graphs.get(graph_id)


def get_graph_data(graph_id: str) -> Optional[dict]:
    return _graph_data.get(graph_id)


def list_graphs() -> list:
    return [
        {
            "graph_id": gid,
            "document_title": data.get("document_title", ""),
            "domain": data.get("domain", ""),
            "node_count": data.get("node_count", 0),
            "edge_count": data.get("edge_count", 0),
        }
        for gid, data in _graph_data.items()
    ]


def delete_graph(graph_id: str) -> bool:
    if graph_id in _graphs:
        del _graphs[graph_id]
        del _graph_data[graph_id]
        return True
    return False
