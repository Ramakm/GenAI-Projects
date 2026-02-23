import logging

from core.llm import get_llm
from agents.state import KnowledgeGraphState

logger = logging.getLogger(__name__)


def _build_summary_prompt(state: KnowledgeGraphState) -> str:
    title = state.get("document_title", "Document")
    domain = state.get("domain", "general")
    node_count = state.get("node_count", 0)
    edge_count = state.get("edge_count", 0)
    density = state.get("graph_density", 0.0)
    cc = state.get("connected_components", 1)
    central = state.get("central_entities", [])
    entity_types = state.get("entity_types_found", [])
    rel_types = state.get("relationship_types_found", [])
    entities = state.get("entities", [])
    relationships = state.get("relationships", [])

    # Top-10 entities for prompt
    entity_lines = "\n".join(
        f"- {e['name']} ({e['entity_type']}): {e.get('description', '')[:100]}"
        for e in entities[:10]
    )
    rel_lines = "\n".join(
        f"- {r['source_name']} --[{r['relationship_type']}]--> {r['target_name']}: {r.get('description','')[:80]}"
        for r in relationships[:10]
    )

    return f"""You are a knowledge graph analyst. Generate a comprehensive natural language summary of this knowledge graph.

Document: {title}
Domain: {domain}
Graph Stats: {node_count} entities, {edge_count} relationships, density={density:.3f}, {cc} connected component(s)
Entity Types: {', '.join(entity_types)}
Relationship Types: {', '.join(rel_types)}
Most Connected Entities: {', '.join(central)}

Sample Entities (first 10):
{entity_lines}

Sample Relationships (first 10):
{rel_lines}

Write a 3–5 paragraph summary covering:
1. Overview of the domain and document
2. Key entities and their roles
3. Most important relationships and clusters
4. Network structure insights (density, connectivity, central nodes)
5. Potential use cases for querying this graph

Be specific and analytical. Reference actual entity names."""


def graph_summarizer(state: KnowledgeGraphState) -> KnowledgeGraphState:
    logger.info("Node 5: graph_summarizer — generating graph summary")
    messages = list(state.get("progress_messages", []))
    messages.append("Generating graph summary...")

    try:
        prompt = _build_summary_prompt(state)
        llm = get_llm()
        response = llm.invoke(prompt)
        summary = response.content.strip()
        messages.append("Graph summary generated.")
        return {
            **state,
            "graph_summary": summary,
            "current_agent": "done",
            "progress_messages": messages,
        }
    except Exception as e:
        logger.error(f"graph_summarizer failed: {e}")
        messages.append(f"Summary error: {e}")
        return {
            **state,
            "graph_summary": f"Summary generation failed: {e}",
            "current_agent": "done",
            "progress_messages": messages,
            "error": str(e),
        }
