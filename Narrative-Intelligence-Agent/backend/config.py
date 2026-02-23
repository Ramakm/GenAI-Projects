import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.2")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
BACKEND_URL  = os.getenv("BACKEND_URL", "http://localhost:8000")
LOG_LEVEL    = os.getenv("LOG_LEVEL", "INFO")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

MAX_ARTICLES          = int(os.getenv("MAX_ARTICLES", "20"))
MAX_ARTICLES_PER_FEED = int(os.getenv("MAX_ARTICLES_PER_FEED", "5"))
SENTIMENT_BATCH_SIZE  = int(os.getenv("SENTIMENT_BATCH_SIZE", "4"))
MAX_NARRATIVES        = int(os.getenv("MAX_NARRATIVES", "8"))
MAX_PATTERNS          = int(os.getenv("MAX_PATTERNS", "5"))
CONTENT_CHAR_LIMIT    = int(os.getenv("CONTENT_CHAR_LIMIT", "600"))

NARRATIVE_TYPES = ["dominant", "emerging", "fading", "contested", "fringe"]
FRAMING_TYPES   = ["positive", "negative", "neutral", "alarmist", "optimistic"]
PATTERN_TYPES   = ["convergence", "divergence", "amplification", "suppression", "reversal", "echo_chamber"]
SENTIMENT_LABELS = ["positive", "negative", "neutral", "mixed"]

# Preset RSS feeds by category
RSS_PRESETS = {
    "general_news": [
        "http://feeds.bbci.co.uk/news/rss.xml",
        "https://feeds.reuters.com/reuters/topNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "https://www.theguardian.com/world/rss",
    ],
    "technology": [
        "https://feeds.feedburner.com/TechCrunch",
        "https://www.wired.com/feed/rss",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.theverge.com/rss/index.xml",
    ],
    "finance": [
        "https://feeds.marketwatch.com/marketwatch/topstories/",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://feeds.bloomberg.com/markets/news.rss",
    ],
    "science": [
        "https://www.sciencedaily.com/rss/top.xml",
        "https://feeds.nature.com/nature/rss/current",
    ],
    "climate": [
        "https://www.theguardian.com/environment/climate-crisis/rss",
        "https://insideclimatenews.org/feed/",
    ],
}

# Preset topic configurations
TOPIC_PRESETS = {
    "ai_tech": {
        "topic": "Artificial Intelligence & Technology",
        "query": "artificial intelligence machine learning AI",
        "feed_category": "technology",
    },
    "climate_change": {
        "topic": "Climate Change & Environment",
        "query": "climate change global warming environment",
        "feed_category": "climate",
    },
    "global_markets": {
        "topic": "Global Financial Markets",
        "query": "stock market economy inflation recession",
        "feed_category": "finance",
    },
    "geopolitics": {
        "topic": "Geopolitics & International Relations",
        "query": "geopolitics international relations conflict diplomacy",
        "feed_category": "general_news",
    },
}
