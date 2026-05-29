# ============================================================
#  AVBOB Lead Assistant — main.py
#  FastAPI backend server
# ============================================================
import os
import asyncio
from contextlib import asynccontextmanager

from fastapi                  import FastAPI
from fastapi.middleware.cors  import CORSMiddleware
from fastapi.responses        import HTMLResponse, RedirectResponse

from database                  import init_db, get_all_leads, get_stats, get_setting
from routes.analyze            import router as analyze_router
from routes.replies            import router as replies_router
from routes.whatsapp           import router as whatsapp_router
from routes.leads              import router as leads_router
from routes.facebook           import router as facebook_router, start_polling_loop
from routes.settings           import router as settings_router


# ── Startup / shutdown ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    fb_token = os.getenv("FB_PAGE_ACCESS_TOKEN") or get_setting("fb_page_access_token")
    if fb_token:
        asyncio.create_task(start_polling_loop())
    else:
        import logging
        logging.getLogger("avbob").warning(
            "FB_PAGE_ACCESS_TOKEN not set — auto-polling disabled. "
            "Add it via /settings or set the FB_PAGE_ACCESS_TOKEN secret."
        )
    yield


# ── App ────────────────────────────────────────────────────────
app = FastAPI(
    title       = "AVBOB Lead Assistant API",
    description = "AI-powered lead generation backend for AVBOB funeral insurance consultants",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],   # Chrome extension has no fixed origin — keep as *
    allow_credentials = False,
    allow_methods     = ["GET", "POST", "OPTIONS"],
    allow_headers     = ["Content-Type", "Authorization"],
)

# ── Routers ────────────────────────────────────────────────────
app.include_router(analyze_router,  tags=["Analysis"])
app.include_router(replies_router,  tags=["Reply Generation"])
app.include_router(whatsapp_router, tags=["WhatsApp"])
app.include_router(leads_router,    tags=["CRM"])
app.include_router(facebook_router, tags=["Facebook"])
app.include_router(settings_router, tags=["Settings"])


# ── Root → dashboard redirect ──────────────────────────────────
@app.get("/", tags=["System"], include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard")


# ── Health ─────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "AVBOB Lead Assistant", "version": "1.0.0"}


# ── Built-in CRM dashboard (HTML) ─────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse, tags=["System"])
def dashboard():
    leads = get_all_leads(limit=200)
    stats = get_stats()
    fb_token = get_setting("fb_page_access_token") or os.getenv("FB_PAGE_ACCESS_TOKEN", "")
    fb_banner = "" if fb_token else (
        '<div style="background:#7c2d12;color:#fca5a5;padding:10px 28px;font-size:12px;font-weight:700;">'
        '⚠️  Facebook token not set — auto-polling is disabled. '
        '<a href="/settings" style="color:#fde68a;text-decoration:underline">Go to Settings →</a>'
        '</div>'
    )
    ai_warning = "" if os.getenv("OPENAI_API_KEY") else (
        '<div style="background:#7c2d12;color:#fca5a5;padding:10px 28px;font-size:12px;font-weight:700;">'
        '⚠️  OPENAI_API_KEY is not set — AI scoring is disabled. Add it in your deployment Secrets to enable full analysis.'
        '</div>'
    )

    def score_badge(s):
        if s >= 75: return f'<span style="color:#22c55e;font-weight:700">{s}</span>'
        if s >= 45: return f'<span style="color:#eab308;font-weight:700">{s}</span>'
        return              f'<span style="color:#ef4444;font-weight:700">{s}</span>'

    def status_badge(st):
        colours = {"new":"#1e3a5f:#60a5fa","contacted":"#1c3d2a:#4ade80",
                   "follow-up":"#3d2a1c:#fb923c","converted":"#2a1c3d:#c084fc"}
        bg, fg = colours.get(st, "#1e293b:#94a3b8").split(":")
        return f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">{st.upper()}</span>'

    rows = "".join(f"""
      <tr>
        <td>{l['id']}</td>
        <td>{l.get('name') or '<em style="color:#4b5563">Unknown</em>'}</td>
        <td title="{l['post_text']}">{l['post_text'][:60]}…</td>
        <td style="text-align:center">{score_badge(l['lead_score'])}/100</td>
        <td style="text-align:center">{l['intent_level'].upper()}</td>
        <td>{status_badge(l['status'])}</td>
        <td>{l.get('language','en').upper()}</td>
        <td style="color:#4b5563;font-size:11px">{l['created_at'][:16]}</td>
        <td>
          <a href="{l['post_url']}" target="_blank"
             style="color:#60a5fa;font-size:11px"
             {"" if l['post_url'] else 'hidden'}>View</a>
        </td>
      </tr>""" for l in leads) or '<tr><td colspan="9" style="text-align:center;color:#4b5563;padding:24px">No leads yet — browse Facebook to detect posts.</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>AVBOB Lead Assistant — Dashboard</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#0D1117;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;font-size:13px}}
    .header{{background:linear-gradient(135deg,#0D1117,#1a2233);padding:18px 28px;border-bottom:2px solid #D4AF37;display:flex;justify-content:space-between;align-items:center}}
    .logo{{font-size:20px;font-weight:800;color:#D4AF37}}
    .subtitle{{color:#64748b;font-size:12px;margin-top:2px}}
    .stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:#1e2d45;border-bottom:1px solid #1e2d45}}
    .stat{{background:#141c2b;padding:14px;text-align:center}}
    .stat-val{{font-size:28px;font-weight:800;color:#D4AF37}}
    .stat-lbl{{font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-top:2px}}
    .content{{padding:20px 28px}}
    .section-title{{font-size:14px;font-weight:700;color:#94a3b8;margin-bottom:14px;text-transform:uppercase;letter-spacing:0.8px}}
    table{{width:100%;border-collapse:collapse;background:#141c2b;border-radius:10px;overflow:hidden}}
    th{{background:#1e2d45;padding:10px 12px;text-align:left;font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.5px}}
    td{{padding:10px 12px;border-bottom:1px solid #1e2d45;vertical-align:middle}}
    tr:last-child td{{border-bottom:none}}
    tr:hover td{{background:#1a2233}}
    .refresh{{background:#D4AF37;color:#0D1117;border:none;padding:8px 18px;border-radius:7px;font-weight:700;cursor:pointer;font-size:13px}}
    .refresh:hover{{background:#c9a227}}
  </style>
</head>
<body>
  {fb_banner}
  {ai_warning}
  <div class="header">
    <div>
      <div class="logo">🤝 AVBOB Lead Assistant</div>
      <div class="subtitle">CRM Dashboard — Powered by AI</div>
    </div>
    <div style="display:flex;gap:10px;align-items:center">
      <a href="/settings" style="color:#94a3b8;text-decoration:none;font-size:12px;font-weight:600;padding:6px 14px;border:1px solid #1e2d45;border-radius:7px">⚙ Settings</a>
      <button class="refresh" onclick="triggerPoll()">↻ Refresh</button>
    </div>
  </div>

  <div class="stats">
    <div class="stat"><div class="stat-val">{stats.get('total',0)}</div><div class="stat-lbl">Total</div></div>
    <div class="stat"><div class="stat-val">{stats.get('new',0)}</div><div class="stat-lbl">New</div></div>
    <div class="stat"><div class="stat-val">{stats.get('contacted',0)}</div><div class="stat-lbl">Contacted</div></div>
    <div class="stat"><div class="stat-val">{stats.get('follow_up',0)}</div><div class="stat-lbl">Follow-up</div></div>
    <div class="stat"><div class="stat-val">{stats.get('converted',0)}</div><div class="stat-lbl">Converted</div></div>
  </div>

  <div class="content">
    <div class="section-title">All Leads ({len(leads)})</div>
    <table>
      <thead>
        <tr>
          <th>#</th><th>Name</th><th>Post Preview</th>
          <th>Score</th><th>Intent</th><th>Status</th>
          <th>Lang</th><th>Saved At</th><th>Link</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <script>
    async function triggerPoll() {{
      const btn = document.querySelector('.refresh');
      btn.textContent = '⏳ Polling…';
      btn.disabled = true;
      try {{
        const r = await fetch('/facebook/poll', {{method:'POST'}});
        const d = await r.json();
        if (d.status === 'ok') {{
          btn.textContent = `✅ ${{d.saved}} new lead${{d.saved !== 1 ? 's' : ''}} found`;
        }} else {{
          btn.textContent = '❌ Poll failed';
        }}
      }} catch(e) {{
        btn.textContent = '❌ Error';
      }}
      setTimeout(() => location.reload(), 1200);
    }}
  </script>
</body>
</html>"""
