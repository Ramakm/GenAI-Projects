import uuid
import logging
from fastapi import APIRouter, HTTPException
from api.models.request import DecisionStoreRequest
from api.models.response import DecisionStoreResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_decision_store: dict[str, dict] = {}


def get_decision(decision_id: str) -> dict | None:
    return _decision_store.get(decision_id)


@router.post("/decisions", response_model=DecisionStoreResponse)
async def store_decision(req: DecisionStoreRequest):
    decision_id = str(uuid.uuid4())[:8]
    _decision_store[decision_id] = {
        "decision_id": decision_id,
        "decision_title": req.decision_title,
        "decision_text": req.decision_text,
        "industry_context": req.industry_context,
        "time_horizon": req.time_horizon,
    }
    logger.info(f"Stored decision: {decision_id} — {req.decision_title}")
    return DecisionStoreResponse(
        decision_id=decision_id,
        decision_title=req.decision_title,
        decision_text=req.decision_text,
        industry_context=req.industry_context,
        time_horizon=req.time_horizon,
        message=f"Decision stored with ID: {decision_id}",
    )


@router.get("/decisions/{decision_id}")
async def get_stored_decision(decision_id: str):
    decision = get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision '{decision_id}' not found")
    return decision
