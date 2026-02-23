import uuid
import logging

from fastapi import APIRouter, HTTPException
from api.models.request import TopicStoreRequest
from api.models.response import TopicStoreResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_topic_store: dict[str, dict] = {}


def get_topic(topic_id: str) -> dict | None:
    return _topic_store.get(topic_id)


@router.post("/topics", response_model=TopicStoreResponse)
async def store_topic(req: TopicStoreRequest):
    topic_id = str(uuid.uuid4())[:8]
    _topic_store[topic_id] = {
        "topic_id": topic_id,
        "topic": req.topic,
        "query": req.query,
        "sources": [s.model_dump() for s in req.sources],
        "time_window": req.time_window,
    }
    logger.info(f"Stored topic '{topic_id}': {req.topic}")
    return TopicStoreResponse(
        topic_id=topic_id,
        topic=req.topic,
        message=f"Topic stored with ID: {topic_id}",
    )


@router.get("/topics/{topic_id}")
async def get_stored_topic(topic_id: str):
    topic = get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")
    return topic
