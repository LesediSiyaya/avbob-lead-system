# ============================================================
#  Routes: /settings  /settings/token
#  Manage app settings — including Facebook token refresh
# ============================================================
import os
import httpx
from fastapi          import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic         import BaseModel
from database         import get_setting, set_setting

router = APIRouter()

GRAPH_URL = "https://graph.facebook.com/v19.0"


class TokenUpdate(BaseModel):
    token: str


async def check_token_health(token: str) -> dict:
    """Verify whether a FB token is still valid."""
    if not token:
        return {"valid": False, "reason": "No token configured"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{GRAPH_URL}/me",
                params={"access_token": token, "fields": "id,name"},
            )
        if r.status_code == 200:
            data = r.json()
            return {"valid": True, "page_name": data.get("name", ""), "page_id": data.get("id", "")}
        err = r.json().get("error", {})
        return {"valid": False, "reason": err.get("message", f"HTTP {r.status_code}")}
    except Exception as e:
        return {"valid": False, "reason": str(e)}


@router.get("/settings/token/health")
async def token_health():
    """Check if the current Facebook token is valid."""
    token = get_setting("fb_page_access_token") or os.getenv("FB_PAGE_ACCESS_TOKEN", "")
    return await check_token_health(token)


@router.post("/settings/token")
async def update_token(payload: TokenUpdate):
    """Save a new Facebook Page Access Token to the database."""
    token = payload.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token cannot be empty")
    health = await check_token_health(token)
    if not health["valid"]:
        raise HTTPException(status_code=400, detail=f"Token is invalid: {health['reason']}")
    set_setting("fb_page_access_token", token)
    return {"message": "Token saved successfully", "page_name": health.get("page_name", "")}


@router.get("/settings", response_class=HTMLResponse)
async def settings_page():
    """Settings dashboard page."""
    token = get_setting("fb_page_access_token") or os.getenv("FB_PAGE_ACCESS_TOKEN", "")
    health = await check_token_health(token)

    if health["valid"]:
        token_status_html = f"""
        <div class="status ok">
            ✅ Token is <strong>active</strong> — connected to page:
            <strong>{health.get('page_name', '')}</strong>
        </div>"""
    else:
        reason = health.get("reason", "Unknown error")
        token_status_html = f"""
        <div class="status error">
            ❌ Token is <strong>invalid or expired</strong><br>
            <small>{reason}</small>
        </div>"""

    masked = (token[:12] + "…" + token[-8:]) if len(token) > 24 else ("Not set" if not token else token)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>AVBOB — Settings</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#0D1117;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;font-size:14px}}
    .header{{background:linear-gradient(135deg,#0D1117,#1a2233);padding:18px 28px;border-bottom:2px solid #D4AF37;display:flex;justify-content:space-between;align-items:center}}
    .logo{{font-size:20px;font-weight:800;color:#D4AF37}}
    .subtitle{{color:#64748b;font-size:12px;margin-top:2px}}
    .nav a{{color:#94a3b8;text-decoration:none;margin-left:18px;font-size:13px;font-weight:600}}
    .nav a:hover{{color:#D4AF37}}
    .content{{max-width:680px;margin:40px auto;padding:0 24px}}
    .card{{background:#141c2b;border:1px solid #1e2d45;border-radius:12px;padding:28px;margin-bottom:24px}}
    .card-title{{font-size:13px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:18px}}
    .status{{padding:12px 16px;border-radius:8px;font-size:13px;margin-bottom:18px;line-height:1.6}}
    .status.ok{{background:#0d2b1a;border:1px solid #166534;color:#86efac}}
    .status.error{{background:#2b0d0d;border:1px solid #991b1b;color:#fca5a5}}
    .field-label{{font-size:12px;color:#64748b;margin-bottom:6px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px}}
    .current-token{{font-family:monospace;font-size:12px;color:#64748b;background:#0d1117;padding:8px 12px;border-radius:6px;margin-bottom:18px}}
    textarea{{width:100%;background:#0d1117;border:1px solid #1e2d45;border-radius:8px;color:#e2e8f0;font-size:13px;font-family:monospace;padding:12px;resize:vertical;min-height:90px;outline:none}}
    textarea:focus{{border-color:#D4AF37}}
    .btn{{background:#D4AF37;color:#0D1117;border:none;padding:10px 22px;border-radius:8px;font-weight:700;cursor:pointer;font-size:13px;margin-top:12px}}
    .btn:hover{{background:#c9a227}}
    .btn-sec{{background:#1e2d45;color:#94a3b8;border:none;padding:10px 22px;border-radius:8px;font-weight:700;cursor:pointer;font-size:13px;margin-top:12px;margin-left:10px}}
    .btn-sec:hover{{background:#2a3d5a}}
    #msg{{margin-top:12px;font-size:13px;min-height:20px}}
    .ok-msg{{color:#86efac}} .err-msg{{color:#fca5a5}}
    .hint{{font-size:12px;color:#4b5563;margin-top:10px;line-height:1.6}}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <div class="logo">🤝 AVBOB Lead Assistant</div>
      <div class="subtitle">Settings</div>
    </div>
    <nav class="nav">
      <a href="/dashboard">← Dashboard</a>
    </nav>
  </div>

  <div class="content">
    <div class="card">
      <div class="card-title">Facebook Page Access Token</div>
      {token_status_html}

      <div class="field-label">Current Token</div>
      <div class="current-token">{masked}</div>

      <div class="field-label">Update Token</div>
      <textarea id="tokenInput" placeholder="Paste new Facebook Page Access Token here…"></textarea>

      <p class="hint">
        To get a new token: go to <strong>developers.facebook.com</strong> →
        your app → Tools → Graph API Explorer → select your page →
        Generate token with <code>pages_read_engagement</code> permission.
      </p>

      <div>
        <button class="btn" onclick="saveToken()">Save & Verify Token</button>
        <button class="btn-sec" onclick="checkHealth()">Check Current Token</button>
      </div>
      <div id="msg"></div>
    </div>
  </div>

  <script>
    async function saveToken() {{
      const token = document.getElementById('tokenInput').value.trim();
      if (!token) {{ showMsg('Please paste a token first', false); return; }}
      showMsg('Verifying…', null);
      try {{
        const r = await fetch('/settings/token', {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{token}})
        }});
        const d = await r.json();
        if (r.ok) {{
          showMsg('✅ Token saved! Connected to: ' + (d.page_name || 'your page'), true);
          setTimeout(() => location.reload(), 1500);
        }} else {{
          showMsg('❌ ' + (d.detail || 'Failed to save token'), false);
        }}
      }} catch(e) {{ showMsg('❌ Network error: ' + e.message, false); }}
    }}

    async function checkHealth() {{
      showMsg('Checking…', null);
      try {{
        const r = await fetch('/settings/token/health');
        const d = await r.json();
        if (d.valid) showMsg('✅ Token is active — page: ' + (d.page_name || ''), true);
        else showMsg('❌ Token invalid: ' + (d.reason || ''), false);
      }} catch(e) {{ showMsg('❌ Error: ' + e.message, false); }}
    }}

    function showMsg(text, ok) {{
      const el = document.getElementById('msg');
      el.textContent = text;
      el.className = ok === true ? 'ok-msg' : ok === false ? 'err-msg' : '';
    }}
  </script>
</body>
</html>"""
