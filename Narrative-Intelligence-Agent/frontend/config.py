import os

BACKEND_URL       = os.getenv("BACKEND_URL", "http://localhost:8000")
HEALTH_ENDPOINT   = f"{BACKEND_URL}/health"
ANALYZE_ENDPOINT  = f"{BACKEND_URL}/api/analyze"
STREAM_ENDPOINT   = f"{BACKEND_URL}/api/analyze/stream"
TOPICS_ENDPOINT   = f"{BACKEND_URL}/api/topics"
FEEDS_ENDPOINT    = f"{BACKEND_URL}/api/feeds/presets"
PRESETS_ENDPOINT  = f"{BACKEND_URL}/api/topics/presets"
