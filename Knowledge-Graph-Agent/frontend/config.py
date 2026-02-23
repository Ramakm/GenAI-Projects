import os

BACKEND_URL      = os.getenv("BACKEND_URL", "http://localhost:8000")
HEALTH_ENDPOINT  = f"{BACKEND_URL}/health"
BUILD_ENDPOINT   = f"{BACKEND_URL}/api/graph/build"
STREAM_ENDPOINT  = f"{BACKEND_URL}/api/graph/build/stream"
GRAPHS_ENDPOINT  = f"{BACKEND_URL}/api/graph"
QUERY_ENDPOINT   = f"{BACKEND_URL}/api/graph/query"
