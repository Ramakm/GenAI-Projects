import json
import logging
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.models.request import BuildGraphRequest
from api.models.response import BuildGraphResponse, EntityResponse, RelationshipResponse, GraphListItem
from agents.pipeline import run_pipeline
from agents.state import KnowledgeGraphState
from agents.document_ingester import document_ingester
from agents.entity_extractor import entity_extractor
from agents.relationship_extractor import relationship_extractor
from agents.graph_builder import graph_builder
from agents.graph_summarizer import _build_summary_prompt
from core.graph_store import get_graph_data, list_graphs
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)
router = APIRouter()


def _state_to_response(state: KnowledgeGraphState) -> BuildGraphResponse:
    entities = [
        EntityResponse(
            entity_id=e["entity_id"],
            name=e["name"],
            entity_type=e["entity_type"],
            description=e.get("description", ""),
            aliases=e.get("aliases", []),
            confidence=e.get("confidence", 0.8),
        )
        for e in state.get("entities", [])
    ]
    relationships = [
        RelationshipResponse(
            rel_id=r.get("rel_id", ""),
            source_entity_id=r.get("source_entity_id", ""),
            target_entity_id=r.get("target_entity_id", ""),
            source_name=r.get("source_name", ""),
            target_name=r.get("target_name", ""),
            relationship_type=r.get("relationship_type", ""),
            description=r.get("description", ""),
            weight=r.get("weight", 0.5),
        )
        for r in state.get("relationships", [])
    ]
    return BuildGraphResponse(
        graph_id=state.get("graph_id", ""),
        document_title=state.get("document_title", ""),
        domain=state.get("domain", ""),
        node_count=state.get("node_count", 0),
        edge_count=state.get("edge_count", 0),
        graph_density=state.get("graph_density", 0.0),
        connected_components=state.get("connected_components", 0),
        central_entities=state.get("central_entities", []),
        entity_types_found=state.get("entity_types_found", []),
        relationship_types_found=state.get("relationship_types_found", []),
        entities=entities,
        relationships=relationships,
        graph_summary=state.get("graph_summary", ""),
        progress_messages=state.get("progress_messages", []),
        error=state.get("error"),
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def _stream_summary_tokens(prompt: str) -> AsyncGenerator[str, None]:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "options": {"temperature": LLM_TEMPERATURE},
    }
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error(f"Summary streaming error: {e}")
        yield f"\n\n[Streaming error: {e}]"


async def _build_stream(req: BuildGraphRequest) -> AsyncGenerator[str, None]:
    state: KnowledgeGraphState = {
        "raw_content": req.raw_content,
        "document_title": req.document_title,
        "domain": req.domain,
        "source_type": req.source_type,
        "source_identifier": req.source_identifier if req.source_identifier != "inline" else req.raw_content[:200],
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

    # --- Node 1: Document Ingester ---
    yield _sse({"event": "agent_start", "agent": "document_ingester", "message": "Ingesting document..."})
    try:
        state = document_ingester(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "document_ingester"})
        return
    yield _sse({
        "event": "agent_complete", "agent": "document_ingester",
        "char_count": state.get("char_count", 0),
        "chunk_count": len(state.get("text_chunks", [])),
    })

    # --- Node 2: Entity Extractor ---
    yield _sse({"event": "agent_start", "agent": "entity_extractor", "message": "Extracting entities..."})
    try:
        state = entity_extractor(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "entity_extractor"})
        return
    for e in state.get("entities", []):
        yield _sse({
            "event": "agent_update", "agent": "entity_extractor",
            "entity_id": e["entity_id"], "name": e["name"], "entity_type": e["entity_type"],
        })
    yield _sse({
        "event": "agent_complete", "agent": "entity_extractor",
        "entity_count": len(state.get("entities", [])),
        "entity_types": state.get("entity_types_found", []),
    })

    # --- Node 3: Relationship Extractor ---
    yield _sse({"event": "agent_start", "agent": "relationship_extractor", "message": "Extracting relationships..."})
    try:
        state = relationship_extractor(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "relationship_extractor"})
        return
    for r in state.get("relationships", []):
        yield _sse({
            "event": "agent_update", "agent": "relationship_extractor",
            "rel_id": r["rel_id"], "source": r["source_name"],
            "target": r["target_name"], "type": r["relationship_type"],
        })
    yield _sse({
        "event": "agent_complete", "agent": "relationship_extractor",
        "relationship_count": len(state.get("relationships", [])),
        "rel_types": state.get("relationship_types_found", []),
    })

    # --- Node 4: Graph Builder ---
    yield _sse({"event": "agent_start", "agent": "graph_builder", "message": "Building knowledge graph..."})
    try:
        state = graph_builder(state)
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "graph_builder"})
        return
    yield _sse({
        "event": "agent_complete", "agent": "graph_builder",
        "graph_id": state.get("graph_id", ""),
        "node_count": state.get("node_count", 0),
        "edge_count": state.get("edge_count", 0),
        "graph_density": state.get("graph_density", 0.0),
        "central_entities": state.get("central_entities", []),
    })

    # --- Node 5: Graph Summarizer (streamed) ---
    yield _sse({"event": "agent_start", "agent": "graph_summarizer", "message": "Generating graph summary..."})
    prompt = _build_summary_prompt(state)
    full_summary = ""
    try:
        async for token in _stream_summary_tokens(prompt):
            full_summary += token
            yield _sse({"event": "token", "token": token})
    except Exception as e:
        yield _sse({"event": "error", "message": str(e), "agent": "graph_summarizer"})
        return

    state = {**state, "graph_summary": full_summary, "current_agent": "done"}
    result = _state_to_response(state)
    yield _sse({"event": "done", "result": result.model_dump()})


@router.post("/graph/build", response_model=BuildGraphResponse)
async def build_graph_blocking(req: BuildGraphRequest):
    logger.info(f"Build graph: {req.document_title}")
    try:
        state = run_pipeline(
            req.raw_content, req.document_title, req.domain,
            req.source_type, req.source_identifier,
        )
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return _state_to_response(state)


@router.post("/graph/build/stream")
async def build_graph_stream(req: BuildGraphRequest):
    logger.info(f"Stream build: {req.document_title}")
    return StreamingResponse(
        _build_stream(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/graph", response_model=list[GraphListItem])
async def list_all_graphs():
    return [GraphListItem(**g) for g in list_graphs()]


@router.get("/graph/{graph_id}", response_model=BuildGraphResponse)
async def get_graph_endpoint(graph_id: str):
    data = get_graph_data(graph_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Graph '{graph_id}' not found")
    entities = [
        EntityResponse(
            entity_id=e["entity_id"], name=e["name"], entity_type=e["entity_type"],
            description=e.get("description", ""), aliases=e.get("aliases", []),
            confidence=e.get("confidence", 0.8),
        )
        for e in data.get("entities", [])
    ]
    relationships = [
        RelationshipResponse(
            rel_id=r.get("rel_id", ""), source_entity_id=r.get("source_entity_id", ""),
            target_entity_id=r.get("target_entity_id", ""), source_name=r.get("source_name", ""),
            target_name=r.get("target_name", ""), relationship_type=r.get("relationship_type", ""),
            description=r.get("description", ""), weight=r.get("weight", 0.5),
        )
        for r in data.get("relationships", [])
    ]
    return BuildGraphResponse(
        graph_id=graph_id,
        document_title=data.get("document_title", ""),
        domain=data.get("domain", ""),
        node_count=data.get("node_count", 0),
        edge_count=data.get("edge_count", 0),
        graph_density=data.get("graph_density", 0.0),
        connected_components=data.get("connected_components", 0),
        central_entities=data.get("central_entities", []),
        entity_types_found=data.get("entity_types_found", []),
        relationship_types_found=data.get("relationship_types_found", []),
        entities=entities,
        relationships=relationships,
        graph_summary=data.get("graph_summary", ""),
        progress_messages=[],
        error=None,
    )


@router.get("/graph/{graph_id}/export")
async def export_graph(graph_id: str):
    data = get_graph_data(graph_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Graph '{graph_id}' not found")
    return {
        "graph_id": graph_id,
        "document_title": data.get("document_title", ""),
        "domain": data.get("domain", ""),
        "metadata": {
            "node_count": data.get("node_count", 0),
            "edge_count": data.get("edge_count", 0),
            "graph_density": data.get("graph_density", 0.0),
            "connected_components": data.get("connected_components", 0),
            "central_entities": data.get("central_entities", []),
        },
        "entities": data.get("entities", []),
        "relationships": data.get("relationships", []),
    }
