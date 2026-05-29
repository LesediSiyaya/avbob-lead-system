# ============================================================
#  Route: /whatsapp-link
# ============================================================
from fastapi   import APIRouter
from models    import PostData, WhatsAppResponse
from ai.engine import generate_whatsapp

router = APIRouter()

@router.post("/whatsapp-link", response_model=WhatsAppResponse)
async def route_whatsapp(payload: PostData):
    result = await generate_whatsapp(
        post_text = payload.text,
        author    = payload.author,
    )
    return WhatsAppResponse(**result)
