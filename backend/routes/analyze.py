# ============================================================
#  Route: /analyze-lead
# ============================================================
from fastapi  import APIRouter
from models   import PostData, AnalyzeResponse
from ai.engine import analyze_lead

router = APIRouter()

@router.post("/analyze-lead", response_model=AnalyzeResponse)
async def route_analyze(payload: PostData):
    result = await analyze_lead(
        post_text        = payload.text,
        author           = payload.author,
        matched_keywords = payload.matched_keywords,
    )
    return AnalyzeResponse(**result)
