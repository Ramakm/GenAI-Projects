import logging

import feedparser

from config import MAX_RSS_ENTRIES

logger = logging.getLogger(__name__)


def fetch_feed_entries(feed_url: str, max_entries: int = MAX_RSS_ENTRIES) -> list[dict]:
    """Fetch and parse RSS/Atom feed entries."""
    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        raise ValueError(f"Failed to fetch feed {feed_url}: {e}")

    if feed.get("bozo") and not feed.get("entries"):
        raise ValueError(f"Invalid or unreachable feed: {feed_url}")

    entries = []
    for entry in feed.entries[:max_entries]:
        title = entry.get("title", "")
        link = entry.get("link", "")
        published = entry.get("published", entry.get("updated", ""))
        summary = entry.get("summary", "")

        content = ""
        if entry.get("content"):
            content = entry["content"][0].get("value", "")

        full_text = " ".join(filter(None, [
            title,
            summary,
            content[:3000] if content else "",
        ]))

        entries.append({
            "title": title,
            "link": link,
            "published": published,
            "summary": summary,
            "content": content[:3000] if content else "",
            "full_text": full_text.strip(),
        })

    return entries
