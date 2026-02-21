import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

HEALTH_ENDPOINT     = f"{BACKEND_URL}/health"
RESEARCH_ENDPOINT   = f"{BACKEND_URL}/api/research"
STREAM_ENDPOINT     = f"{BACKEND_URL}/api/research/stream"
