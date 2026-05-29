# ============================================================
#  Route: /generate-reply
# ============================================================
from fastapi   import APIRouter
from models    import PostData, ReplyResponse
from ai.engine import analyze_lead, generate_reply

router = APIRouter()

@router.post("/generate-reply", response_model=ReplyResponse)
async def route_reply(payload: PostData):
    # Score first if we don't have intent yet
    analysis = await analyze_lead(
        post_text        = payload.text,
        author           = payload.author,
        matched_keywords = payload.matched_keywords,
    )
    result = await generate_reply(
        post_text = payload.text,
        author    = payload.author,
        intent    = analysis["intent"],
        score     = analysis["score"],
    )
    return ReplyResponse(**result)
