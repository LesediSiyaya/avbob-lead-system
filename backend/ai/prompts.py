# ============================================================
#  AVBOB Lead Assistant — ai/prompts.py
#  Structured prompt templates for lead scoring & reply gen
# ============================================================

SYSTEM_AVBOB = """You are an expert AI assistant for AVBOB funeral insurance consultants in South Africa.
AVBOB is South Africa's largest mutual assurance society, providing funeral cover and burial services
to all communities for over 100 years. Your role is to help consultants identify genuine leads
and craft ethical, empathetic, non-spammy responses.

IMPORTANT RULES:
- Never suggest auto-sending messages or bypassing platform rules
- Always maintain respect and empathy — funeral cover is a sensitive topic
- Be culturally aware of South Africa's diverse communities
- Responses must feel personal, not like mass marketing
- All suggestions require human review before use"""


# ── Lead analysis prompt ───────────────────────────────────────
def build_analyze_prompt(post_text: str, author: str, matched_keywords: list) -> str:
    kw_str = ", ".join(matched_keywords) if matched_keywords else "detected via pattern"
    return f"""Analyze this Facebook post from a potential funeral insurance lead.

POST AUTHOR: {author}
POST TEXT:
\"\"\"
{post_text}
\"\"\"

MATCHED KEYWORDS: {kw_str}

Your task:
1. Score this lead from 0–100 based on purchase intent and urgency
2. Classify intent as: low / medium / high
3. Write a 1–2 sentence summary of why this is (or isn't) a strong lead
4. List the 2–4 most relevant keywords you detected
5. Detect the language (use ISO 639-1 code, e.g. en, zu, af, xh, st, tn)

Scoring guide:
- 80–100 = HIGH: Actively seeking cover right now, urgent need, or recent bereavement
- 50–79  = MEDIUM: Genuine interest, comparing options, or asking for information
- 0–49   = LOW: Vague curiosity, sharing info, or not clearly a prospect

Respond ONLY with valid JSON — no markdown, no explanation:
{{
  "score": <integer 0-100>,
  "intent": "<low|medium|high>",
  "summary": "<1-2 sentence explanation>",
  "matched_keywords": ["<kw1>", "<kw2>"],
  "language": "<iso code>"
}}"""


# ── Reply generation prompt ────────────────────────────────────
def build_reply_prompt(post_text: str, author: str, intent: str, score: int) -> str:
    urgency = {
        "high":   "This is an urgent, high-intent lead. Be warm, direct, and offer clear next steps.",
        "medium": "This person has genuine interest. Be helpful and informative without being pushy.",
        "low":    "This person is in early research mode. Be educational and plant a seed of interest.",
    }.get(intent, "Be professional and empathetic.")

    return f"""Write a Facebook comment reply for an AVBOB consultant to post manually on this prospect's post.

PROSPECT: {author}
LEAD SCORE: {score}/100 ({intent.upper()} intent)
POST TEXT:
\"\"\"
{post_text}
\"\"\"

INSTRUCTIONS:
- {urgency}
- Write in the SAME LANGUAGE as the post (if not English, match the language)
- Keep it under 100 words — natural and conversational
- Do NOT include prices or specific policy details (too early)
- DO mention AVBOB's trusted reputation and free, no-obligation consultation
- End with a gentle call to action (DM, WhatsApp, or comment)
- Sound like a real helpful person, NOT a sales bot
- Do NOT use bullet points — write as natural flowing text

Return ONLY the reply text. No JSON, no explanations, no quotes around it."""


# ── WhatsApp message prompt ────────────────────────────────────
def build_whatsapp_prompt(post_text: str, author: str) -> str:
    first_name = author.split()[0] if author and author != "Unknown" else "there"
    return f"""Write a WhatsApp follow-up message an AVBOB consultant will send MANUALLY to this prospect.

PROSPECT FIRST NAME: {first_name}
POST CONTEXT:
\"\"\"
{post_text}
\"\"\"

INSTRUCTIONS:
- Write in the SAME LANGUAGE as the post (match the language)
- Friendly, warm, and empathetic opening
- Reference what they posted about (show you read it)
- Introduce yourself briefly as an AVBOB consultant
- Offer a free consultation with no obligation
- Keep it under 80 words
- End with a clear, single question or CTA
- DO NOT mention specific premium amounts

Return ONLY the WhatsApp message text. No JSON, no quotes, no formatting."""
