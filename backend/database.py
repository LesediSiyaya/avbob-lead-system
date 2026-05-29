# ============================================================
#  AVBOB Lead Assistant — database.py
#  PostgreSQL via psycopg2 (Supabase)
# ============================================================
import os
import psycopg2
import psycopg2.extras
from datetime import datetime
from typing   import List, Optional, Dict, Any

DB_URL = os.getenv("SUPABASE_DATABASE_URL", "")


SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id           SERIAL PRIMARY KEY,
    name         TEXT,
    post_text    TEXT    NOT NULL,
    post_url     TEXT    NOT NULL DEFAULT '',
    lead_score   INTEGER NOT NULL DEFAULT 0,
    intent_level TEXT    NOT NULL DEFAULT 'low',
    status       TEXT    NOT NULL DEFAULT 'new',
    language     TEXT    NOT NULL DEFAULT 'en',
    created_at   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_leads_status  ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_score   ON leads(lead_score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at DESC);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def get_conn():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    return conn


def init_db() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
    print("✅  Supabase database ready")


# ── CRUD ────────────────────────────────────────────────────────
def insert_lead(
    name:         Optional[str],
    post_text:    str,
    post_url:     str,
    lead_score:   int,
    intent_level: str,
    language:     str = "en",
) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO leads
                   (name, post_text, post_url, lead_score, intent_level, status, language, created_at)
                   VALUES (%s, %s, %s, %s, %s, 'new', %s, %s)
                   RETURNING *""",
                (name, post_text, post_url, lead_score, intent_level, language, now),
            )
            row = cur.fetchone()
        conn.commit()
    return dict(row)


def get_lead_by_id(lead_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM leads WHERE id = %s", (lead_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def get_all_leads(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM leads ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (limit, offset),
            )
            rows = cur.fetchall()
    return [dict(r) for r in rows]


def update_lead_status(lead_id: int, status: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE leads SET status = %s WHERE id = %s", (status, lead_id)
            )
            affected = cur.rowcount
        conn.commit()
    return affected > 0


def get_stats() -> Dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COUNT(*)                                              AS total,
                    SUM(CASE WHEN status='new'       THEN 1 ELSE 0 END)  AS new,
                    SUM(CASE WHEN status='contacted' THEN 1 ELSE 0 END)  AS contacted,
                    SUM(CASE WHEN status='follow-up' THEN 1 ELSE 0 END)  AS follow_up,
                    SUM(CASE WHEN status='converted' THEN 1 ELSE 0 END)  AS converted,
                    ROUND(AVG(lead_score::NUMERIC), 1)                   AS avg_score
                FROM leads
            """)
            row = cur.fetchone()
    return dict(row) if row else {}


def lead_exists(post_text: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM leads WHERE post_text = %s LIMIT 1", (post_text,)
            )
            row = cur.fetchone()
    return row is not None


# ── Settings (key/value store) ──────────────────────────────────
def get_setting(key: str, default: str = "") -> str:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM settings WHERE key = %s", (key,))
                row = cur.fetchone()
        return row[0] if row else default
    except Exception:
        return default


def set_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO settings (key, value) VALUES (%s, %s)
                   ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
                (key, value),
            )
        conn.commit()
