# Deployment Guide — AVBOB Lead Assistant

## Overview

The system has two independently deployable parts:
1. **Backend** — Python FastAPI server (this Replit workspace)
2. **Chrome Extension** — loaded unpacked in Chrome (no deployment needed)

---

## 1. Backend Deployment (Replit)

### Required Secrets

Set these in **Replit → Tools → Secrets** before deploying:

| Secret | Required | Description |
|--------|----------|-------------|
| `SUPABASE_DATABASE_URL` | Yes | PostgreSQL connection string, e.g. `postgresql://user:pass@host:5432/db` |
| `OPENAI_API_KEY` | Recommended | Enables AI lead scoring. Without it, falls back to keyword scoring. |
| `FB_PAGE_ACCESS_TOKEN` | Optional | Facebook Page token for auto-polling your page every 10 minutes |
| `FB_VERIFY_TOKEN` | Optional | For Facebook webhook verification |

### Deploy Steps

1. Set the required secrets above
2. Click **Deploy** in the Replit UI (or use the Deploy button)
3. Note the deployed URL — it will look like `https://your-repl-name.replit.app`
4. Verify it's working: visit `https://your-repl-name.replit.app/health`
   - Expected response: `{"status":"ok","service":"AVBOB Lead Assistant","version":"1.0.0"}`

### Production Run Command

```
cd artifacts/avbob-backend && uvicorn main:app --host 0.0.0.0 --port 5000
```

---

## 2. Chrome Extension Setup

The extension connects to the deployed backend via a configurable URL.

### Load the Extension

1. Open Chrome → navigate to `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked**
4. Select the `extension/` folder in this workspace
5. The AVBOB icon appears in your Chrome toolbar

### Set the Backend URL

1. Click the AVBOB extension icon
2. Click the **⚙ Settings** gear icon
3. Enter your deployed backend URL (e.g. `https://your-repl-name.replit.app`)
4. Click **Save** — the status dot should turn green (Connected)

> The URL is saved in Chrome's local storage — you only need to do this once.

---

## 3. Environment Variable Reference

```
# Required
SUPABASE_DATABASE_URL=postgresql://user:password@host:5432/database

# Recommended — enables AI scoring
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini          # default, cheapest fast model

# Optional — Facebook integration
FB_PAGE_ACCESS_TOKEN=              # from Facebook Developers → Graph API Explorer
FB_VERIFY_TOKEN=any_random_string  # must match what you enter in Facebook webhook settings

# Optional — local AI fallback (no OpenAI key needed)
USE_OLLAMA=false
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

---

## 4. API URL Contract

The backend exposes all endpoints at **root** — no `/api` prefix:

```
GET  /health
GET  /get-leads?limit=100&offset=0
GET  /stats
GET  /dashboard
POST /save-lead
POST /analyze-lead
POST /generate-reply
POST /whatsapp-link
POST /update-status/{id}
POST /facebook/poll
GET  /settings
POST /settings/token
GET  /settings/token/health
```

The Chrome extension's `background.js` constructs URLs as `${backendUrl}${path}` where `backendUrl` is the base URL **without a trailing slash** and paths start with `/`.

---

## 5. Verifying the Integration

After deploying backend and loading the extension:

1. Visit `https://your-backend.replit.app/health` → should return `{"status":"ok",...}`
2. Visit `https://your-backend.replit.app/dashboard` → shows the CRM dashboard
3. Open the extension popup → status dot should be **green (Connected)**
4. Browse a Facebook group — posts with funeral cover keywords will get an AVBOB toolbar injected

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Extension shows "Offline" | Wrong backend URL | Open Settings in popup, correct the URL |
| Extension shows "Offline" | Backend not running | Check Replit workflow is running |
| `500` errors on `/save-lead` | `SUPABASE_DATABASE_URL` not set | Add the secret in Replit → Secrets |
| `AI unavailable` in analysis | `OPENAI_API_KEY` missing | Add key to Replit Secrets (extension still works without it) |
| No Facebook posts detected | Content script not running | Refresh the Facebook tab after loading the extension |
