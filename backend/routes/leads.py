# ============================================================
#  Routes: /save-lead  /get-leads  /update-status  /stats
# ============================================================
from fastapi  import APIRouter, HTTPException, Path
from typing   import List
from models   import SaveLeadRequest, LeadRecord, StatsResponse, UpdateStatusRequest
from database import insert_lead, get_all_leads, update_lead_status, get_stats, lead_exists
from ai.engine import analyze_lead

router = APIRouter()


@router.post("/save-lead")
async def route_save_lead(payload: SaveLeadRequest):
    """Score the post with AI then persist it to SQLite."""

    # De-duplicate
    if lead_exists(payload.text):
        return {"message": "Lead already saved", "duplicate": True}

    # AI analysis
    analysis = await analyze_lead(
        post_text        = payload.text,
        author           = payload.author,
        matched_keywords = [],
    )

    lead = insert_lead(
        name         = payload.author if payload.author != "Unknown" else None,
        post_text    = payload.text,
        post_url     = payload.postUrl,
        lead_score   = analysis["score"],
        intent_level = analysis["intent"],
        language     = analysis.get("language", "en"),
    )
    return {"message": "Lead saved", "lead": lead}


@router.get("/get-leads", response_model=List[LeadRecord])
def route_get_leads(limit: int = 100, offset: int = 0):
    return get_all_leads(limit=limit, offset=offset)


@router.post("/update-status/{lead_id}")
def route_update_status(
    lead_id: int = Path(..., description="Lead ID"),
    payload: UpdateStatusRequest = ...,
):
    ok = update_lead_status(lead_id, payload.status.value)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
    return {"message": "Status updated", "id": lead_id, "status": payload.status}


@router.get("/stats", response_model=StatsResponse)
def route_stats():
    data = get_stats()
    return StatsResponse(
        total     = data.get("total", 0)     or 0,
        new       = data.get("new", 0)       or 0,
        contacted = data.get("contacted", 0) or 0,
        follow_up = data.get("follow_up", 0) or 0,
        converted = data.get("converted", 0) or 0,
        avg_score = data.get("avg_score", 0) or 0.0,
    )
