from typing import TypedDict


class Entity(TypedDict):
    entity_id: str        # "E001"…
    name: str
    entity_type: str      # from ENTITY_TYPES
    description: str
    aliases: list         # alternative names
    confidence: float     # 0.0–1.0


class Relationship(TypedDict):
    rel_id: str           # "R001"…
    source_entity_id: str
    target_entity_id: str
    source_name: str
    target_name: str
    relationship_type: str   # from RELATIONSHIP_TYPES
    description: str
    weight: float            # 0.0–1.0 confidence/strength


class KnowledgeGraphState(TypedDict):
    # Input
    raw_content: str
    document_title: str
    domain: str
    source_type: str          # "text" | "url"
    source_identifier: str
    # Node 1 — Document Ingester
    parsed_text: str
    text_chunks: list
    char_count: int
    # Node 2 — Entity Extractor
    entities: list            # list[Entity]
    entity_types_found: list
    # Node 3 — Relationship Extractor
    relationships: list       # list[Relationship]
    relationship_types_found: list
    # Node 4 — Graph Builder
    graph_id: str
    node_count: int
    edge_count: int
    graph_density: float
    connected_components: int
    central_entities: list    # top-5 entity names by degree centrality
    # Node 5 — Graph Summarizer
    graph_summary: str
    # Progress
    current_agent: str
    progress_messages: list
    error: str                # None allowed
