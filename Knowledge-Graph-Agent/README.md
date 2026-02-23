# Knowledge Graph Agent

A 5-node LangGraph agent that extracts entities and relationships from any domain document and builds a queryable knowledge graph with interactive visualization.

## Architecture

```
Document Ingester → Entity Extractor → Relationship Extractor → Graph Builder → Graph Summarizer
```

| Node | Responsibility |
|------|---------------|
| **Document Ingester** | Parse text / fetch URL, clean and chunk into 1500-char segments |
| **Entity Extractor** | LLM JSON extraction per chunk, deduplication, ID assignment |
| **Relationship Extractor** | LLM JSON extraction against known entity list, deduplication |
| **Graph Builder** | Build NetworkX DiGraph, compute density/centrality/components, store in-memory |
| **Graph Summarizer** | Stream a 3–5 paragraph natural language summary of the graph |

### Separate Query Engine (`core/query_engine.py`)

| Query Type | Trigger | Algorithm |
|------------|---------|-----------|
| Neighborhood | 1 entity name in query | `nx.ego_graph(radius=2)` |
| Path Finding | 2+ entity names in query | `nx.shortest_path` on undirected view |
| Keyword Search | No entity names matched | Term scoring on entity names + descriptions |

## Stack

- **Backend**: FastAPI + LangGraph + NetworkX + Ollama (llama3.2)
- **Frontend**: Streamlit + pyvis (interactive graph)
- **Storage**: In-memory `dict[str, nx.DiGraph]` (graph store)

## Entity & Relationship Types

**Entity types:** PERSON · ORGANIZATION · TECHNOLOGY · CONCEPT · LOCATION · EVENT · PRODUCT · PROCESS

**Relationship types:** WORKS_FOR · PART_OF · USES · CAUSES · IS_A · RELATED_TO · COMPETES_WITH · LOCATED_IN · DEVELOPS · FOUNDED_BY · LEADS · OWNS · COLLABORATES_WITH · DEPENDS_ON · PRECEDES · FOLLOWS

## Quick Start

```bash
ollama pull llama3.2

# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend && pip install -r requirements.txt
streamlit run app.py
```

Or via Make:
```bash
make install-backend install-frontend
make run-backend    # terminal 1
make run-frontend   # terminal 2
```

### Docker

```bash
docker compose up --build -d
docker exec kga-ollama ollama pull llama3.2
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | System health check |
| POST | `/api/graph/build` | Blocking graph build |
| POST | `/api/graph/build/stream` | SSE streaming build |
| GET | `/api/graph` | List all built graphs |
| GET | `/api/graph/{id}` | Get graph data |
| GET | `/api/graph/{id}/export` | Export full graph as JSON |
| POST | `/api/graph/query` | Semantic graph query |

## Frontend Tabs

- **Build Graph** — Document input + 5-agent streaming progress + live summary
- **Explore Graph** — Entity table (filterable by type) + relationship table + interactive pyvis network + downloads
- **Query Graph** — Natural language query → auto-detected query type → sub-graph visualization + LLM answer

## Config

| Variable | Default | Description |
|----------|---------|-------------|
| `CHUNK_SIZE` | 1500 | Characters per text chunk |
| `MAX_CHUNKS` | 6 | Max chunks processed per document |
| `MAX_ENTITIES_PER_CHUNK` | 10 | Max entities extracted per chunk |
| `MAX_RELS_PER_CHUNK` | 8 | Max relationships extracted per chunk |
| `MAX_GRAPH_NODES` | 200 | Global entity cap |
