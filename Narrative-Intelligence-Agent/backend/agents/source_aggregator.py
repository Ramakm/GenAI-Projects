import logging
import time
from urllib.parse import urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup

from agents.state import NarrativeIntelligenceState
from config import MAX_ARTICLES, MAX_ARTICLES_PER_FEED, CONTENT_CHAR_LIMIT

logger = logging.getLogger(__name__)


def _clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return url[:40]


def _parse_rss(feed_url: str) -> list:
    articles = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
            title = getattr(entry, "title", "Untitled")
            link  = getattr(entry, "link", feed_url)
            # content: prefer full content over summary
            content_raw = ""
            if hasattr(entry, "content") and entry.content:
                content_raw = entry.content[0].get("value", "")
            if not content_raw:
                content_raw = getattr(entry, "summary", "") or getattr(entry, "description", "")
            content = _clean_html(content_raw)[:CONTENT_CHAR_LIMIT]

            published = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = time.strftime("%Y-%m-%dT%H:%M:%SZ", entry.published_parsed)
                except Exception:
                    published = ""

            articles.append({
                "title": title,
                "url": link,
                "content": content,
                "published_at": published,
                "source": _domain(feed_url),
                "source_type": "rss",
            })
    except Exception as e:
        logger.warning(f"RSS parse failed for {feed_url}: {e}")
    return articles


def _fetch_url(url: str) -> dict:
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; NIA-bot/1.0)"})
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else _domain(url)
        content = soup.get_text(separator=" ", strip=True)[:CONTENT_CHAR_LIMIT]
        return {
            "title": title,
            "url": url,
            "content": content,
            "published_at": "",
            "source": _domain(url),
            "source_type": "url",
        }
    except Exception as e:
        logger.warning(f"URL fetch failed for {url}: {e}")
        return {}


def source_aggregator(state: NarrativeIntelligenceState) -> NarrativeIntelligenceState:
    logger.info("Node 1: source_aggregator — aggregating media sources")
    messages = list(state.get("progress_messages", []))
    messages.append("Aggregating sources...")

    sources_input = state.get("sources_input", [])
    raw_articles: list = []

    for source in sources_input:
        stype = source.get("type", "text")
        value = source.get("value", "").strip()
        label = source.get("label", "")

        if not value:
            continue

        if stype == "rss":
            entries = _parse_rss(value)
            raw_articles.extend(entries)
            messages.append(f"RSS '{_domain(value)}': {len(entries)} articles")

        elif stype == "url":
            item = _fetch_url(value)
            if item:
                raw_articles.append(item)
                messages.append(f"URL '{_domain(value)}': fetched")

        elif stype == "text":
            name = label or f"text_source_{len(raw_articles)+1}"
            raw_articles.append({
                "title": label or "Pasted content",
                "url": "",
                "content": value[:CONTENT_CHAR_LIMIT],
                "published_at": "",
                "source": name[:40],
                "source_type": "text",
            })
            messages.append(f"Text source '{name}': {len(value):,} chars")

    # Deduplicate by URL (keep first occurrence)
    seen_urls: set = set()
    unique: list = []
    for a in raw_articles:
        url = a.get("url", "")
        key = url if url else id(a)
        if key not in seen_urls:
            seen_urls.add(key)
            unique.append(a)

    # Limit total
    articles_raw = unique[:MAX_ARTICLES]

    # Assign IDs
    articles = []
    for i, a in enumerate(articles_raw):
        articles.append({
            "article_id": f"A{i+1:03d}",
            "source": a["source"],
            "title": a["title"],
            "content": a["content"],
            "url": a.get("url", ""),
            "published_at": a.get("published_at", ""),
            "source_type": a["source_type"],
        })

    sources_found = sorted(set(a["source"] for a in articles))
    messages.append(
        f"Collected {len(articles)} articles from {len(sources_found)} sources: {', '.join(sources_found[:6])}"
    )

    return {
        **state,
        "articles": articles,
        "article_count": len(articles),
        "sources_found": sources_found,
        "current_agent": "source_aggregator",
        "progress_messages": messages,
    }
