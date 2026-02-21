import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.2")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
MAX_URLS        = int(os.getenv("MAX_URLS", "10"))
FETCH_TIMEOUT   = int(os.getenv("FETCH_TIMEOUT", "10"))
MAX_TEXT_CHARS  = int(os.getenv("MAX_TEXT_CHARS", "4000"))
