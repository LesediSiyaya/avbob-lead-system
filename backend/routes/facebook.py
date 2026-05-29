# ============================================================
#  Routes: /facebook/poll  /webhook/facebook
#  Polls your Facebook Page for new posts every 10 minutes
#  and scores them as leads automatically.
# ============================================================
import os
import logging
import asyncio
import httpx
from fastapi        import APIRouter, Request, Response, HTTPException
from database       import insert_lead, lead_exists, get_setting
from ai.engine      import analyze_lead

logger = logging.getLogger("avbob.facebook")
router = APIRouter()

GRAPH_URL = "https://graph.facebook.com/v19.0"

# Track last poll time for the status endpoint
_last_poll_result: dict = {"status": "never_run", "saved": 0, "skipped": 0, "last_run": None}


# ── Core polling logic (shared by background task + manual trigger) ─
async def poll_facebook_page() -> dict:
    global _last_poll_result
    FB_PAGE_ACCESS_TOKEN = get_setting("fb_page_access_token") or os.getenv("FB_PAGE_ACCESS_TOKEN", "")
    if not FB_PAGE_ACCESS_TOKEN:
        logger.error("FB_PAGE_ACCESS_TOKEN is not set — cannot poll")
        return {"status": "error", "reason": "FB_PAGE_ACCESS_TOKEN not configured"}

    params = {
        "access_token": FB_PAGE_ACCESS_TOKEN,
        "fields": "message,from,permalink_url,created_time",
        "limit": 25,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{GRAPH_URL}/me/feed", params=params)

    if r.status_code != 200:
        logger.error("Facebook API error %s: %s", r.status_code, r.text)
        return {"status": "error", "reason": f"Facebook API returned {r.status_code}"}

    posts = r.json().get("data", [])
    saved = 0
    skipped = 0

    for post in posts:
        post_text = (post.get("message") or "").strip()
        if not post_text:
            skipped += 1
            continue

        if lead_exists(post_text):
            skipped += 1
            continue

        author    = (post.get("from") or {}).get("name", "Unknown")
        post_url  = post.get("permalink_url", "")

        try:
            analysis = await analyze_lead(
                post_text        = post_text,
                author           = author,
                matched_keywords = [],
            )
            insert_lead(
                name         = author if author != "Unknown" else None,
                post_text    = post_text,
                post_url     = post_url,
                lead_score   = analysis["score"],
                intent_level = analysis["intent"],
                language     = analysis.get("language", "en"),
            )
            saved += 1
            logger.info("Lead saved from FB poll — %s (score=%s)", author, analysis["score"])
        except Exception as exc:
            logger.error("Failed to process post: %s", exc)
            skipped += 1

    from datetime import datetime, timezone
    logger.info("FB poll complete: saved=%d skipped=%d", saved, skipped)
    result = {"status": "ok", "saved": saved, "skipped": skipped, "total_posts": len(posts),
              "last_run": datetime.now(timezone.utc).isoformat()}
    _last_poll_result = result
    return result


# ── Background polling task (runs every 10 minutes) ────────────
async def start_polling_loop():
    await asyncio.sleep(10)
    while True:
        try:
            logger.info("Running scheduled Facebook poll…")
            await poll_facebook_page()
        except Exception as exc:
            logger.error("Polling loop error: %s", exc)
        await asyncio.sleep(600)


# ── Manual trigger endpoint ─────────────────────────────────────
@router.post("/facebook/poll", tags=["Facebook"])
async def route_poll():
    """Manually trigger a Facebook page poll right now."""
    result = await poll_facebook_page()
    return result


# ── Facebook status endpoint ────────────────────────────────────
@router.get("/facebook/status", tags=["Facebook"])
def fb_status():
    """Return current polling status and token health (non-blocking)."""
    token = get_setting("fb_page_access_token") or os.getenv("FB_PAGE_ACCESS_TOKEN", "")
    return {
        "token_configured": bool(token),
        "token_preview": (token[:8] + "…") if len(token) > 8 else ("not set" if not token else token),
        "polling_active": bool(token),
        "poll_interval_seconds": 600,
        **_last_poll_result,
    }


# ── Webhook verification ─────────────────────────────────────────
@router.get("/webhook/facebook", tags=["Facebook"])
def fb_verify(request: Request):
    mode      = request.query_params.get("hub.mode")
    token     = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    FB_VERIFY_TOKEN = get_setting("fb_verify_token") or os.getenv("FB_VERIFY_TOKEN", "")
    if not FB_VERIFY_TOKEN:
        raise HTTPException(status_code=500, detail="FB_VERIFY_TOKEN not configured")
    if mode == "subscribe" and token == FB_VERIFY_TOKEN:
        logger.info("Facebook webhook verified")
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/facebook", tags=["Facebook"])
async def fb_events(request: Request):
    body = await request.json()
    if body.get("object") != "page":
        return {"status": "ignored"}
    saved = skipped = 0
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "feed":
                continue
            value     = change.get("value", {})
            post_text = (value.get("message") or "").strip()
            if not post_text or lead_exists(post_text):
                skipped += 1
                continue
            author   = (value.get("from") or {}).get("name", "Unknown")
            post_url = value.get("permalink_url", "")
            try:
                analysis = await analyze_lead(post_text=post_text, author=author, matched_keywords=[])
                insert_lead(
                    name=author if author != "Unknown" else None,
                    post_text=post_text, post_url=post_url,
                    lead_score=analysis["score"], intent_level=analysis["intent"],
                    language=analysis.get("language", "en"),
                )
                saved += 1
            except Exception as exc:
                logger.error("Webhook post error: %s", exc)
                skipped += 1
    return {"status": "ok", "saved": saved, "skipped": skipped}
