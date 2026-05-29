# ============================================================
#  AVBOB Lead Assistant — models.py
# ============================================================
from pydantic import BaseModel, Field
from typing   import Optional, List
from datetime import datetime
from enum     import Enum


# ── Enums ──────────────────────────────────────────────────────
class IntentLevel(str, Enum):
    low    = "low"
    medium = "medium"
    high   = "high"

class LeadStatus(str, Enum):
    new        = "new"
    contacted  = "contacted"
    follow_up  = "follow-up"
    converted  = "converted"


# ── Request bodies ─────────────────────────────────────────────
class PostData(BaseModel):
    text:             str  = Field(..., description="Facebook post text")
    author:           str  = Field(default="Unknown", description="Author's display name")
    postUrl:          str  = Field(default="",        description="URL of the Facebook post")
    matched_keywords: List[str] = Field(default=[],   description="Keywords already matched client-side")


class SaveLeadRequest(BaseModel):
    text:     str = Field(..., alias="text")
    author:   str = Field(default="Unknown", alias="author")
    postUrl:  str = Field(default="",        alias="postUrl")

    model_config = {"populate_by_name": True}


class UpdateStatusRequest(BaseModel):
    status: LeadStatus


# ── Response models ────────────────────────────────────────────
class AnalyzeResponse(BaseModel):
    score:            int          # 0–100
    intent:           IntentLevel
    summary:          str
    matched_keywords: List[str]
    language:         str = "en"   # detected language code


class ReplyResponse(BaseModel):
    reply:        str
    tone:         str
    channel_hint: str = "Facebook comment / WhatsApp message"


class WhatsAppResponse(BaseModel):
    message:      str
    link:         str    # wa.me link with pre-filled text
    phone_prompt: str    # reminder for consultant to add number


class LeadRecord(BaseModel):
    id:           int
    name:         Optional[str]
    post_text:    str
    post_url:     str
    lead_score:   int
    intent_level: str
    status:       str
    created_at:   str


class StatsResponse(BaseModel):
    total:      int
    new:        int
    contacted:  int
    follow_up:  int
    converted:  int
    avg_score:  float
