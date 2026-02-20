import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

# Endpoint URLs
HEALTH_URL = f"{BACKEND_URL}/health"
UPLOAD_URL = f"{BACKEND_URL}/api/documents/upload"
DOCUMENTS_URL = f"{BACKEND_URL}/api/documents"
QUERY_URL = f"{BACKEND_URL}/api/query"
STREAM_URL = f"{BACKEND_URL}/api/query/stream"

# UI defaults
SUPPORTED_TYPES = ["pdf", "docx", "txt", "md", "html", "csv", "xlsx", "pptx"]
DEFAULT_TOP_K = 5
MAX_TOP_K = 20

# Timeouts (seconds)
HEALTH_TIMEOUT = 5
UPLOAD_TIMEOUT = 120
QUERY_TIMEOUT = 120
STREAM_TIMEOUT = 300
