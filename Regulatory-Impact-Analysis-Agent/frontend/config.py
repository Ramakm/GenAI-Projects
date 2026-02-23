import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

HEALTH_ENDPOINT       = f"{BACKEND_URL}/health"
INGEST_PDF_ENDPOINT   = f"{BACKEND_URL}/api/ingest/pdf"
INGEST_URL_ENDPOINT   = f"{BACKEND_URL}/api/ingest/url"
INGEST_TEXT_ENDPOINT  = f"{BACKEND_URL}/api/ingest/text"
INGEST_RSS_ENDPOINT   = f"{BACKEND_URL}/api/ingest/rss"
ANALYZE_ENDPOINT      = f"{BACKEND_URL}/api/analyze"
STREAM_ENDPOINT       = f"{BACKEND_URL}/api/analyze/stream"
FEEDS_LIST_ENDPOINT   = f"{BACKEND_URL}/api/feeds/list"
FEEDS_POLL_ENDPOINT   = f"{BACKEND_URL}/api/feeds/poll"
