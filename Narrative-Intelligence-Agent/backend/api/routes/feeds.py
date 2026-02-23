from fastapi import APIRouter
from config import RSS_PRESETS, TOPIC_PRESETS

router = APIRouter()


@router.get("/feeds/presets")
async def get_feed_presets():
    return {"presets": RSS_PRESETS, "categories": list(RSS_PRESETS.keys())}


@router.get("/topics/presets")
async def get_topic_presets():
    return {"presets": TOPIC_PRESETS}
