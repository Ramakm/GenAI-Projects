import logging

from fastapi import APIRouter, HTTPException, Query

from api.models.response import FeedPollResponse, FeedEntry, KnownFeed
from core.rss_poller import fetch_feed_entries
from config import KNOWN_REGULATORY_FEEDS, MAX_RSS_ENTRIES

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/feeds/poll", response_model=FeedPollResponse)
def poll_feed(
    feed_url: str = Query(..., description="RSS/Atom feed URL"),
    max_entries: int = Query(5, ge=1, le=MAX_RSS_ENTRIES),
):
    """Poll a specific RSS/Atom feed and return entries."""
    try:
        entries = fetch_feed_entries(feed_url, max_entries=max_entries)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Feed poll error: {e}")
        raise HTTPException(status_code=500, detail=f"Feed error: {e}")

    feed_entries = [
        FeedEntry(
            title=e["title"],
            link=e["link"],
            published=e["published"],
            summary=e["summary"][:500] if e["summary"] else "",
            content_preview=e["content"][:300] if e["content"] else "",
        )
        for e in entries
    ]

    return FeedPollResponse(
        feed_title=feed_url,
        feed_url=feed_url,
        entry_count=len(feed_entries),
        entries=feed_entries,
    )


@router.get("/feeds/list", response_model=list[KnownFeed])
def list_known_feeds():
    """Return the list of known regulatory feeds."""
    return [
        KnownFeed(
            name=f["name"],
            url=f["url"],
            industry=f["industry"],
            issuing_body=f["issuing_body"],
        )
        for f in KNOWN_REGULATORY_FEEDS
    ]
