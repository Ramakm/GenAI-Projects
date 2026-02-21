import json
import logging
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, LLM_TEMPERATURE, FETCH_TIMEOUT, MAX_TEXT_CHARS
from agents.state import ResearchState, SourceInfo

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return url


def _fetch_text(url: str) -> tuple[str, Optional[str]]:
    """Returns (text, error). error is None on success."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text[:MAX_TEXT_CHARS], None
    except requests.exceptions.Timeout:
        return "", f"timeout after {FETCH_TIMEOUT}s"
    except requests.exceptions.HTTPError as e:
        return "", f"HTTP {e.response.status_code}"
    except Exception as e:
        return "", str(e)


def _extract_claims(text: str, topic: str, llm: ChatOllama) -> list[str]:
    """Ask LLM to extract 3-8 specific factual claims from text."""
    prompt = (
        f"Extract 3–8 specific, verifiable factual claims relevant to the topic "
        f"'{topic}' from the following text. "
        f"Respond with JSON only in this exact format: {{\"claims\": [\"claim1\", \"claim2\", ...]}}\n\n"
        f"Text:\n{text}"
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        claims = data.get("claims", [])
        return [str(c) for c in claims if c][:8]
    except Exception as e:
        logger.warning(f"Failed to parse claims JSON: {e}")
        return []


def gather_sources(state: ResearchState) -> ResearchState:
    """Agent 1: Fetch each URL, extract text, extract claims via LLM."""
    topic = state["topic"]
    urls = state["urls"]
    sources: list[SourceInfo] = []
    failed_urls: list[str] = []
    progress: list[str] = list(state.get("progress_messages", []))

    progress.append(f"[source_gatherer] Starting — fetching {len(urls)} URL(s)...")

    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=LLM_TEMPERATURE,
    )

    for url in urls:
        domain = _extract_domain(url)
        logger.info(f"Fetching: {url}")
        text, error = _fetch_text(url)

        if error:
            logger.warning(f"Failed to fetch {url}: {error}")
            progress.append(f"[source_gatherer] FAILED: {url} — {error}")
            failed_urls.append(url)
            source: SourceInfo = {
                "url": url,
                "domain": domain,
                "raw_text": "",
                "key_claims": [],
                "fetch_error": error,
            }
            sources.append(source)
            continue

        char_count = len(text)
        progress.append(f"[source_gatherer] Fetched: {domain} ({char_count} chars)")
        logger.info(f"Extracted {char_count} chars from {domain}. Running LLM claim extraction...")

        claims = _extract_claims(text, topic, llm)
        progress.append(f"[source_gatherer] Extracted {len(claims)} claims from {domain}")

        source = {
            "url": url,
            "domain": domain,
            "raw_text": text,
            "key_claims": claims,
            "fetch_error": None,
        }
        sources.append(source)

    ok_count = sum(1 for s in sources if s["fetch_error"] is None)
    progress.append(
        f"[source_gatherer] Complete — {ok_count} ok, {len(failed_urls)} failed"
    )

    return {
        **state,
        "sources": sources,
        "failed_urls": failed_urls,
        "progress_messages": progress,
        "current_agent": "source_gatherer",
    }
