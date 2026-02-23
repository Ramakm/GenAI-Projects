import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.2")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
MAX_DECISION_CHARS = int(os.getenv("MAX_DECISION_CHARS", "8000"))
DEFAULT_SCENARIOS  = int(os.getenv("DEFAULT_SCENARIOS", "4"))
MAX_RISKS          = int(os.getenv("MAX_RISKS", "10"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
LOG_LEVEL   = os.getenv("LOG_LEVEL", "INFO")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

DECISION_TYPES = [
    "market_entry", "product_launch", "acquisition", "divestiture",
    "cost_restructuring", "pricing_change", "partnership",
    "technology_investment", "capacity_expansion", "regulatory_response",
]

RISK_CATEGORIES = ["market", "operational", "financial", "strategic", "regulatory"]
