import os

BACKEND_URL        = os.getenv("BACKEND_URL", "http://localhost:8000")
HEALTH_ENDPOINT    = f"{BACKEND_URL}/health"
SIMULATE_ENDPOINT  = f"{BACKEND_URL}/api/simulate"
STREAM_ENDPOINT    = f"{BACKEND_URL}/api/simulate/stream"
DECISIONS_ENDPOINT = f"{BACKEND_URL}/api/decisions"
