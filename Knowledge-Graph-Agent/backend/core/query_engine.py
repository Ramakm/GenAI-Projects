import logging
import time

import networkx as nx

from core.graph_store import get_graph, get_graph_data
from core.llm import get_llm

logger = logging.getLogger(__name__)


def _find_mentioned_entities(G: nx.DiGraph, query_text: str) -> list:
    """Return node IDs whose name or aliases appear in the query text."""
    q_lower = query_text.lower()
    found = []
    for node, data in G.nodes(data=True):
        name = data.get("name", "").lower()
        aliases = [a.lower() for a in data.get("aliases", [])]
        if name and name in q_lower:
            found.append(node)
            continue
        if any(a and a in q_lower for a in aliases):
            found.append(node)
    return found


def _keyword_search(G: nx.DiGraph, query_text: str, max_results: int) -> list:
    words = {w for w in query_text.lower().split() if len(w) > 3}
    scored = []
    for node, data in G.nodes(data=True):
        name = data.get("name", "").lower()
        desc = data.get("description", "").lower()
        et   = data.get("entity_type", "").lower()
        score = sum(1 for w in words if w in name or w in desc or w in et)
        if score > 0:
            scored.append((score, node))
    scored.sort(reverse=True)
    return [node for _, node in scored[:max_results]]


def _collect_edges(G: nx.DiGraph, nodes: set) -> list:
    edges = []
    for u, v, data in G.edges(data=True):
        if u in nodes and v in nodes:
            edges.append({**data, "source_entity_id": u, "target_entity_id": v})
    return edges


def _generate_answer(query_text: str, result_entities: list, result_relationships: list) -> str:
    if not result_entities:
        return "No relevant entities found in the knowledge graph for this query."

    entity_lines = "\n".join(
        f"- {e.get('name', '')} ({e.get('entity_type', '')}): {e.get('description', '')[:120]}"
        for e in result_entities[:10]
    )
    rel_lines = "\n".join(
        f"- {r.get('source_name', '')} --[{r.get('relationship_type', '')}]--> {r.get('target_name', '')}: {r.get('description', '')[:80]}"
        for r in result_relationships[:10]
    )

    prompt = f"""You are a knowledge graph assistant. Answer the user's question using only the graph context below.

Question: {query_text}

Relevant Entities:
{entity_lines}

Relevant Relationships:
{rel_lines}

Provide a concise, accurate answer based solely on the graph context. If the graph does not contain enough information, say so."""

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        return f"Found {len(result_entities)} entities and {len(result_relationships)} relationships. (Answer generation error: {e})"


def query_graph(graph_id: str, query_text: str, max_results: int = 15) -> dict:
    t0 = time.time()
    G = get_graph(graph_id)
    if G is None:
        return {"error": f"Graph '{graph_id}' not found", "graph_id": graph_id}

    result_nodes: set = set()
    result_edges: list = []
    query_type = "semantic"

    mentioned = _find_mentioned_entities(G, query_text)

    if len(mentioned) >= 2:
        query_type = "path_finding"
        G_undir = G.to_undirected()
        for i in range(len(mentioned)):
            for j in range(i + 1, len(mentioned)):
                src, tgt = mentioned[i], mentioned[j]
                try:
                    path = nx.shortest_path(G_undir, src, tgt)
                    result_nodes.update(path)
                except nx.NetworkXNoPath:
                    result_nodes.update([src, tgt])
                except nx.NodeNotFound:
                    pass
        result_edges = _collect_edges(G, result_nodes)

    elif len(mentioned) == 1:
        query_type = "neighborhood"
        center = mentioned[0]
        try:
            ego = nx.ego_graph(G, center, radius=2, undirected=True)
            result_nodes.update(ego.nodes)
            result_edges = _collect_edges(G, result_nodes)
        except Exception:
            result_nodes.add(center)

    else:
        query_type = "keyword_search"
        kw_nodes = _keyword_search(G, query_text, max_results)
        result_nodes.update(kw_nodes)
        result_edges = _collect_edges(G, result_nodes)

    # Build result dicts
    result_entities = [
        {**G.nodes[n], "entity_id": n}
        for n in list(result_nodes)[:max_results]
        if G.has_node(n)
    ]
    # Attach source/target names to edges if missing
    enriched_edges = []
    for edge in result_edges[:max_results]:
        src_id = edge.get("source_entity_id", "")
        tgt_id = edge.get("target_entity_id", "")
        edge = dict(edge)
        if not edge.get("source_name") and G.has_node(src_id):
            edge["source_name"] = G.nodes[src_id].get("name", src_id)
        if not edge.get("target_name") and G.has_node(tgt_id):
            edge["target_name"] = G.nodes[tgt_id].get("name", tgt_id)
        enriched_edges.append(edge)

    answer = _generate_answer(query_text, result_entities, enriched_edges)
    elapsed_ms = round((time.time() - t0) * 1000, 1)

    return {
        "graph_id": graph_id,
        "query_text": query_text,
        "query_type": query_type,
        "result_entities": result_entities,
        "result_relationships": enriched_edges,
        "answer": answer,
        "query_time_ms": elapsed_ms,
    }
