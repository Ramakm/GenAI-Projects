import logging

import httpx
from bs4 import BeautifulSoup

from config import FETCH_TIMEOUT, MAX_DOC_CHARS

logger = logging.getLogger(__name__)

_REMOVE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "noscript"]


async def scrape_url(url: str) -> str:
    """Fetch a URL and return cleaned text content."""
    try:
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 RegulatoryAnalysisBot/1.0"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPStatusError as e:
        raise ValueError(f"HTTP {e.response.status_code} fetching {url}")
    except Exception as e:
        raise ValueError(f"Failed to fetch {url}: {e}")

    soup = BeautifulSoup(html, "lxml")
    for tag in _REMOVE_TAGS:
        for el in soup.find_all(tag):
            el.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cleaned = "\n".join(lines)

    if len(cleaned) > MAX_DOC_CHARS:
        cleaned = cleaned[:MAX_DOC_CHARS]
    return cleaned
