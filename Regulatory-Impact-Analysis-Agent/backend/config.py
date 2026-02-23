import os
from dotenv import load_dotenv

load_dotenv()

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

# Document limits
MAX_DOC_CHARS = int(os.getenv("MAX_DOC_CHARS", "12000"))
FETCH_TIMEOUT = int(os.getenv("FETCH_TIMEOUT", "15"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))

# Defaults
DEFAULT_INDUSTRY = os.getenv("DEFAULT_INDUSTRY", "auto")
MAX_RSS_ENTRIES = int(os.getenv("MAX_RSS_ENTRIES", "10"))

# Server
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Known regulatory RSS feeds
KNOWN_REGULATORY_FEEDS: list[dict] = [
    {
        "name": "Federal Reserve Press Releases",
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "industry": "financial_services",
        "issuing_body": "Federal Reserve",
    },
    {
        "name": "OCC News Releases",
        "url": "https://www.occ.treas.gov/news-issuances/news-releases/rss/news-releases.xml",
        "industry": "financial_services",
        "issuing_body": "OCC",
    },
    {
        "name": "CFPB Newsroom",
        "url": "https://www.consumerfinance.gov/about-us/newsroom/feed/",
        "industry": "financial_services",
        "issuing_body": "CFPB",
    },
    {
        "name": "SEC Press Releases",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&dateb=&owner=include&count=40&search_text=&output=atom",
        "industry": "financial_services",
        "issuing_body": "SEC",
    },
    {
        "name": "EBA News",
        "url": "https://www.eba.europa.eu/rss/news-all",
        "industry": "financial_services",
        "issuing_body": "EBA",
    },
    {
        "name": "FDA News Releases",
        "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
        "industry": "healthcare",
        "issuing_body": "FDA",
    },
    {
        "name": "FDA Guidance Documents",
        "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/guidance/rss.xml",
        "industry": "healthcare",
        "issuing_body": "FDA",
    },
    {
        "name": "CMS Newsroom",
        "url": "https://www.cms.gov/newsroom/rss/news",
        "industry": "healthcare",
        "issuing_body": "CMS",
    },
    {
        "name": "EMA Press Releases",
        "url": "https://www.ema.europa.eu/en/news/rss",
        "industry": "healthcare",
        "issuing_body": "EMA",
    },
]
