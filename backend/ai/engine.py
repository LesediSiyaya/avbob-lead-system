# ============================================================
#  AVBOB Lead Assistant — ai/engine.py
#  Primary: OpenAI (gpt-4o-mini)   Fallback: Ollama (local LLM)
# ============================================================
import os, json, re, logging
from typing import Any, Dict

from ai.prompts import (
    SYSTEM_AVBOB,
    build_analyze_prompt,
    build_reply_prompt,
    build_whatsapp_prompt,
)

logger = logging.getLogger("avbob.ai")

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL    = os.getenv("OPENAI_MODEL",    "gpt-4o-mini")
OLLAMA_URL      = os.getenv("OLLAMA_URL",      "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",    "llama3")
USE_OLLAMA      = os.getenv("USE_OLLAMA",      "false").lower() == "true"


# ── Low-level call ─────────────────────────────────────────────
async def _call_openai(user_prompt: str, system: str = SYSTEM_AVBOB) -> str:
    import httpx
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system",  "content": system},
            {"role": "user",    "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens":  600,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


async def _call_ollama(user_prompt: str, system: str = SYSTEM_AVBOB) -> str:
    import httpx
    body = {
        "model": OLLAMA_MODEL,
        "prompt": f"{system}\n\n{user_prompt}",
        "stream": False,
        "options": {"temperature": 0.4, "num_predict": 600},
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{OLLAMA_URL}/api/generate", json=body)
        r.raise_for_status()
        return r.json().get("response", "").strip()


async def _call_llm(user_prompt: str, system: str = SYSTEM_AVBOB) -> str:
    """Route to OpenAI or Ollama based on config/availability."""
    if USE_OLLAMA or not OPENAI_API_KEY:
        logger.info("Using Ollama (%s)", OLLAMA_MODEL)
        return await _call_ollama(user_prompt, system)
    logger.info("Using OpenAI (%s)", OPENAI_MODEL)
    return await _call_openai(user_prompt, system)


def _parse_json(raw: str) -> Dict[str, Any]:
    """Extract JSON from LLM response, handling markdown fences."""
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    return json.loads(cleaned)


# ── Public API ─────────────────────────────────────────────────
async def analyze_lead(post_text: str, author: str, matched_keywords: list) -> Dict[str, Any]:
    prompt = build_analyze_prompt(post_text, author, matched_keywords)
    try:
        raw  = await _call_llm(prompt)
        data = _parse_json(raw)
        # Validate / clamp
        data["score"]  = max(0, min(100, int(data.get("score", 0))))
        data["intent"] = data.get("intent", "low").lower()
        if data["intent"] not in ("low", "medium", "high"):
            data["intent"] = "low"
        data.setdefault("summary",          "Analysis complete.")
        data.setdefault("matched_keywords", matched_keywords)
        data.setdefault("language",         "en")
        return data
    except Exception as e:
        logger.error("analyze_lead failed: %s", e)
        return _fallback_analyze(post_text, matched_keywords)


async def generate_reply(post_text: str, author: str, intent: str, score: int) -> Dict[str, Any]:
    prompt = build_reply_prompt(post_text, author, intent, score)
    try:
        reply = await _call_llm(prompt)
        return {
            "reply":        reply,
            "tone":         _tone_for_intent(intent),
            "channel_hint": "Facebook comment or WhatsApp — review before sending",
        }
    except Exception as e:
        logger.error("generate_reply failed: %s", e)
        return {
            "reply":        _fallback_reply(author),
            "tone":         "warm",
            "channel_hint": "Review before sending",
        }


async def generate_whatsapp(post_text: str, author: str) -> Dict[str, Any]:
    prompt = build_whatsapp_prompt(post_text, author)
    try:
        message = await _call_llm(prompt)
        link    = f"https://wa.me/?text={_url_encode(message)}"
        return {
            "message":      message,
            "link":         link,
            "phone_prompt": "Replace 'wa.me/' with 'wa.me/27XXXXXXXXX/' to open a specific contact.",
        }
    except Exception as e:
        logger.error("generate_whatsapp failed: %s", e)
        msg = _fallback_whatsapp(author)
        return {
            "message":      msg,
            "link":         f"https://wa.me/?text={_url_encode(msg)}",
            "phone_prompt": "Add the recipient's number to the wa.me URL.",
        }


# ── Fallbacks (no AI / error) ──────────────────────────────────
def _fallback_analyze(text: str, kws: list) -> Dict[str, Any]:
    text_lower = text.lower()
    score  = 55 if any(k in text_lower for k in ["passed", "died", "cover", "policy", "avbob"]) else 30
    intent = "medium" if score >= 50 else "low"
    return {
        "score":            score,
        "intent":           intent,
        "summary":          "AI unavailable — basic keyword scoring used. Review manually.",
        "matched_keywords": kws,
        "language":         "en",
    }

def _fallback_reply(author: str) -> str:
    first = author.split()[0] if author and author != "Unknown" else "there"
    return (
        f"Hi {first}! 👋 I saw your post and would love to help you find the right funeral cover. "
        f"I'm an AVBOB consultant — South Africa's most trusted funeral group. "
        f"Feel free to DM me or WhatsApp me for a free, no-obligation chat. 🙏"
    )

def _fallback_whatsapp(author: str) -> str:
    first = author.split()[0] if author and author != "Unknown" else "there"
    return (
        f"Hi {first}! I noticed your post about funeral cover and wanted to reach out. "
        f"I'm an AVBOB consultant and I'd love to help your family get the right cover. "
        f"Would you have 10 minutes for a free chat? 🙏"
    )

def _tone_for_intent(intent: str) -> str:
    return {"high": "urgent & empathetic", "medium": "helpful & informative", "low": "educational"}.get(intent, "warm")

def _url_encode(text: str) -> str:
    from urllib.parse import quote
    return quote(text, safe='')
