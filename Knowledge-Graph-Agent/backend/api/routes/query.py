import logging

from fastapi import APIRouter, HTTPException

from api.models.request import QueryGraphRequest
from api.models.response import QueryResponse, EntityResponse, RelationshipResponse
from core.query_engine import query_graph
from core.graph_store import get_graph_data

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/graph/query", response_model=QueryResponse)
async def query_graph_endpoint(req: QueryGraphRequest):
    if not get_graph_data(req.graph_id):
        raise HTTPException(status_code=404, detail=f"Graph '{req.graph_id}' not found")

    logger.info(f"Query '{req.graph_id}': {req.query_text[:60]}")
    result = query_graph(req.graph_id, req.query_text, req.max_results)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    entities = [
        EntityResponse(
            entity_id=e.get("entity_id", ""),
            name=e.get("name", ""),
            entity_type=e.get("entity_type", ""),
            description=e.get("description", ""),
            aliases=e.get("aliases", []),
            confidence=e.get("confidence", 0.8),
        )
        for e in result.get("result_entities", [])
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
        for r in result.get("result_relationships", [])
    ]

    return QueryResponse(
        graph_id=req.graph_id,
        query_text=req.query_text,
        query_type=result.get("query_type", "semantic"),
        result_entities=entities,
        result_relationships=relationships,
        answer=result.get("answer", ""),
        query_time_ms=result.get("query_time_ms", 0.0),
    )
