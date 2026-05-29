// ============================================================
//  AVBOB Lead Assistant — background.js  (MV3 Service Worker)
//  Bridges content_script ↔ FastAPI backend
// ============================================================
'use strict';

const DEFAULT_BACKEND = 'https://zip-hub--lesedisiyaya.replit.app';

// ── Message router ─────────────────────────────────────────────
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  handleMessage(message)
    .then(sendResponse)
    .catch(err => sendResponse({ success: false, error: err.message }));
  return true; // keep channel open for async
});

async function handleMessage({ type, data, backendUrl }) {
  const base = backendUrl || DEFAULT_BACKEND;

  switch (type) {
    case 'ANALYZE_LEAD':   return apiPost(base, '/analyze-lead',    data);
    case 'GENERATE_REPLY': return apiPost(base, '/generate-reply',  data);
    case 'SAVE_LEAD':      return apiPost(base, '/save-lead',       data);
    case 'WHATSAPP_LINK':  return apiPost(base, '/whatsapp-link',   data);
    case 'GET_LEADS':      return apiGet (base, '/get-leads');
    case 'GET_STATS':      return apiGet (base, '/stats');
    case 'HEALTH':         return apiGet (base, '/health');
    case 'UPDATE_STATUS':
      return apiPost(base, `/update-status/${data.id}`, { status: data.status });
    default:
      return { success: false, error: `Unknown message type: ${type}` };
  }
}

// ── HTTP helpers ───────────────────────────────────────────────
async function apiPost(base, path, body) {
  try {
    const res = await fetch(`${base}${path}`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    });
    if (!res.ok) {
      const txt = await res.text();
      return { success: false, error: `Server error ${res.status}: ${txt.slice(0, 120)}` };
    }
    const data = await res.json();
    return { success: true, data };
  } catch (e) {
    return { success: false, error: `Cannot reach backend (${base}). Is it running?` };
  }
}

async function apiGet(base, path) {
  try {
    const res = await fetch(`${base}${path}`, {
      method:  'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) return { success: false, error: `Server error ${res.status}` };
    const data = await res.json();
    return { success: true, data };
  } catch (e) {
    return { success: false, error: `Cannot reach backend. Is it running?` };
  }
}
