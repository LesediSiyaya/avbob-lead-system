# AVBOB Lead Assistant

AI-powered funeral insurance lead detection and CRM for AVBOB consultants in South Africa.

## How it works

- **Chrome Extension** — detects funeral cover keywords in Facebook posts and injects an action toolbar. Consultants can AI-analyse a post, generate a reply, get a WhatsApp follow-up link, and save the lead to the CRM — all without leaving Facebook.
- **FastAPI Backend** — scores leads with OpenAI, stores them in PostgreSQL (Supabase), and exposes a built-in CRM dashboard at `/dashboard`.

## Quick Start

### 1. Run the backend

```bash
# Install dependencies
pip install -r requirements.txt

# Set required environment variables (see .env.example)
export SUPABASE_DATABASE_URL="postgresql://user:pass@host:5432/db"
export OPENAI_API_KEY="sk-proj-..."     # optional — falls back to keyword scoring

# Start the server
cd backend
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

Visit `http://localhost:5000/dashboard` to see the CRM dashboard.

### 2. Load the Chrome extension

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `extension/` folder
4. Click the AVBOB icon → **⚙ Settings** → enter your backend URL
5. Browse Facebook groups — posts with funeral cover keywords get an action toolbar

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_DATABASE_URL` | Yes | PostgreSQL connection string |
| `OPENAI_API_KEY` | Recommended | AI lead scoring (falls back to keywords if missing) |
| `FB_PAGE_ACCESS_TOKEN` | Optional | Auto-poll your Facebook Page every 10 min |
| `FB_VERIFY_TOKEN` | Optional | Facebook webhook verification |

See `.env.example` for the full list with comments.

## API Endpoints

All served at root — no `/api` prefix:

```
GET  /health              Health check
GET  /get-leads           List all leads
POST /save-lead           Score + persist a lead
POST /analyze-lead        AI-score a post
POST /generate-reply      Generate Facebook reply
POST /whatsapp-link       Generate WhatsApp follow-up
POST /update-status/{id}  Update lead status
GET  /stats               Lead statistics
GET  /dashboard           CRM dashboard (HTML)
```

## Deployment

See [DEPLOY.md](DEPLOY.md) for full deployment instructions (Replit, Railway, Render).
