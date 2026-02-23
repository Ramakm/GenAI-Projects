import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.2")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
BACKEND_URL  = os.getenv("BACKEND_URL", "http://localhost:8000")
LOG_LEVEL    = os.getenv("LOG_LEVEL", "INFO")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

CHUNK_SIZE              = int(os.getenv("CHUNK_SIZE", "1500"))
CHUNK_OVERLAP           = int(os.getenv("CHUNK_OVERLAP", "200"))
MAX_CHUNKS              = int(os.getenv("MAX_CHUNKS", "6"))
MAX_ENTITIES_PER_CHUNK  = int(os.getenv("MAX_ENTITIES_PER_CHUNK", "10"))
MAX_RELS_PER_CHUNK      = int(os.getenv("MAX_RELS_PER_CHUNK", "8"))
MAX_GRAPH_NODES         = int(os.getenv("MAX_GRAPH_NODES", "200"))
MAX_QUERY_RESULTS       = int(os.getenv("MAX_QUERY_RESULTS", "15"))

ENTITY_TYPES = [
    "PERSON", "ORGANIZATION", "TECHNOLOGY", "CONCEPT",
    "LOCATION", "EVENT", "PRODUCT", "PROCESS",
]

RELATIONSHIP_TYPES = [
    "WORKS_FOR", "PART_OF", "USES", "CAUSES", "IS_A", "RELATED_TO",
    "COMPETES_WITH", "LOCATED_IN", "DEVELOPS", "FOUNDED_BY", "LEADS",
    "OWNS", "COLLABORATES_WITH", "DEPENDS_ON", "PRECEDES", "FOLLOWS",
]
