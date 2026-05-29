# AVBOB Lead Assistant

AI-powered funeral insurance lead detection and CRM for AVBOB consultants in South Africa.

## How it works

The backend automatically polls your Facebook Page for posts mentioning funeral cover keywords, scores them with AI, and stores qualified leads in PostgreSQL (Supabase). Consultants view and manage leads through the React PWA dashboard.

```
React PWA  →  /api/*  →  TypeScript Proxy  →  Python FastAPI  →  Supabase + OpenAI
                                                     ↑
                                              Facebook Page API
                                           (auto-polled every 10 min)
```

## Quick Start — Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Set required environment variables
export SUPABASE_DATABASE_URL="postgresql://user:pass@host:5432/db"
export OPENAI_API_KEY="sk-proj-..."            # optional — falls back to keyword scoring
export FB_PAGE_ACCESS_TOKEN="your-token"       # or store it via /settings

# Start the Python backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

Visit `/api/dashboard` to see the CRM dashboard.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_DATABASE_URL` | Yes | PostgreSQL connection string |
| `OPENAI_API_KEY` | Recommended | AI lead scoring |
| `FB_PAGE_ACCESS_TOKEN` | Optional | Auto-poll Facebook Page (also settable via `/api/settings`) |
| `FB_VERIFY_TOKEN` | Optional | Facebook webhook verification |

## API Endpoints

All accessible at the `/api` prefix:

```
GET  /api/health              Health check
GET  /api/get-leads           List all leads
POST /api/save-lead           Score + persist a lead
POST /api/analyze-lead        AI-score a post
POST /api/generate-reply      Generate Facebook reply
POST /api/whatsapp-link       Generate WhatsApp follow-up
POST /api/update-status/{id}  Update lead status
GET  /api/stats               Lead statistics
GET  /api/dashboard           CRM dashboard (HTML)
POST /api/facebook/poll       Manually trigger Facebook poll
GET/POST /api/settings        Token management
```

## Deployment

See [DEPLOY.md](DEPLOY.md) for full deployment instructions (Replit, Railway, Render).
