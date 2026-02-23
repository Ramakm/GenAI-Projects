from typing import Optional
from pydantic import BaseModel


class EntityResponse(BaseModel):
    entity_id: str
    name: str
    entity_type: str
    description: str
    aliases: list[str]
    confidence: float


class RelationshipResponse(BaseModel):
    rel_id: str
    source_entity_id: str
    target_entity_id: str
    source_name: str
    target_name: str
    relationship_type: str
    description: str
    weight: float


class BuildGraphResponse(BaseModel):
    graph_id: str
    document_title: str
    domain: str
    node_count: int
    edge_count: int
    graph_density: float
    connected_components: int
    central_entities: list[str]
    entity_types_found: list[str]
    relationship_types_found: list[str]
    entities: list[EntityResponse]
    relationships: list[RelationshipResponse]
    graph_summary: str
    progress_messages: list[str]
    error: Optional[str]


class GraphListItem(BaseModel):
    graph_id: str
    document_title: str
    domain: str
    node_count: int
    edge_count: int


class QueryResponse(BaseModel):
    graph_id: str
    query_text: str
    query_type: str
    result_entities: list[EntityResponse]
    result_relationships: list[RelationshipResponse]
    answer: str
    query_time_ms: float


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    model_available: bool
    model: str
    version: str = "1.0.0"
