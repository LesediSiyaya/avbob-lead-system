// ============================================================
//  AVBOB Lead Assistant — popup.js
// ============================================================
'use strict';

const DEFAULT_URL = 'https://zip-hub--lesedisiyaya.replit.app';
let backendUrl    = DEFAULT_URL;
let allLeads      = [];

// ── DOM refs ───────────────────────────────────────────────────
const $  = (id) => document.getElementById(id);
const statusDot      = $('statusDot');
const statusText     = $('statusText');
const leadsList      = $('leadsList');
const statTotal      = $('statTotal');
const statNew        = $('statNew');
const statConverted  = $('statConverted');
const backendUrlInput= $('backendUrlInput');
const settingsHint   = $('settingsHint');
const modalOverlay   = $('modalOverlay');
const modalContent   = $('modalContent');

// ── Helpers ────────────────────────────────────────────────────
function send(type, data = {}) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type, data, backendUrl }, (res) => {
      resolve(res || { success: false, error: 'No response' });
    });
  });
}

function scoreClass(s) {
  return s >= 75 ? 'score-high' : s >= 45 ? 'score-mid' : 'score-low';
}

function badgeClass(status) {
  const map = {
    new: 'badge-new', contacted: 'badge-contacted',
    'follow-up': 'badge-follow-up', converted: 'badge-converted',
  };
  return map[status] || 'badge-new';
}

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1)  return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// ── Connection check ───────────────────────────────────────────
async function checkHealth() {
  statusText.textContent = 'Checking…';
  statusDot.className = 'dot';

  const res = await send('HEALTH');
  if (res.success) {
    statusDot.className = 'dot online';
    statusText.textContent = 'Connected';
  } else {
    statusDot.className = 'dot offline';
    statusText.textContent = 'Offline';
  }
  return res.success;
}

// ── Load and render leads ──────────────────────────────────────
async function loadLeads() {
  leadsList.innerHTML = '<div class="spinner-wrap"><div class="mini-spinner"></div></div>';
  const res = await send('GET_LEADS');

  if (!res.success) {
    leadsList.innerHTML = `
      <div class="empty">
        <div class="empty-icon">⚠️</div>
        <div>Cannot connect to backend.<br>Start the server and refresh.</div>
      </div>`;
    return;
  }

  allLeads = res.data || [];

  // Update stats
  statTotal.textContent    = allLeads.length;
  statNew.textContent      = allLeads.filter(l => l.status === 'new').length;
  statConverted.textContent= allLeads.filter(l => l.status === 'converted').length;

  if (allLeads.length === 0) {
    leadsList.innerHTML = `
      <div class="empty">
        <div class="empty-icon">📭</div>
        <div>No leads yet.<br>Browse Facebook groups to detect posts.</div>
      </div>`;
    return;
  }

  // Render newest 12
  const recent = [...allLeads].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 12);
  leadsList.innerHTML = recent.map(lead => `
    <div class="lead-item" data-id="${lead.id}">
      <div class="lead-top">
        <div class="lead-author">${escHtml(lead.name || 'Unknown')}</div>
        <div class="lead-score ${scoreClass(lead.lead_score)}">${lead.lead_score}/100</div>
      </div>
      <div class="lead-text">${escHtml((lead.post_text || '').slice(0, 70))}…</div>
      <div class="lead-meta">
        <span class="badge ${badgeClass(lead.status)}">${lead.status}</span>
        <span class="badge badge-source">${lead.intent_level} intent</span>
        <span class="badge badge-source">${timeAgo(lead.created_at)}</span>
      </div>
    </div>
  `).join('');

  // Click → detail modal
  leadsList.querySelectorAll('.lead-item').forEach(el => {
    el.addEventListener('click', () => {
      const lead = allLeads.find(l => String(l.id) === el.dataset.id);
      if (lead) openModal(lead);
    });
  });
}

// ── Lead detail modal ──────────────────────────────────────────
function openModal(lead) {
  const waUrl = `https://wa.me/?text=${encodeURIComponent(`Hi, I saw your post about funeral cover. I'm an AVBOB consultant and would love to assist. ${lead.post_url || ''}`)}`;

  modalContent.innerHTML = `
    <div class="modal-title">🤝 Lead #${lead.id} — ${escHtml(lead.name || 'Unknown')}</div>

    <div class="modal-field">
      <div class="modal-field-lbl">Post Text</div>
      <div class="modal-field-val">${escHtml((lead.post_text || '').slice(0, 200))}${lead.post_text?.length > 200 ? '…' : ''}</div>
    </div>

    <div class="modal-field">
      <div class="modal-field-lbl">Score / Intent</div>
      <div class="modal-field-val ${scoreClass(lead.lead_score)}">${lead.lead_score}/100 — ${lead.intent_level?.toUpperCase()} INTENT</div>
    </div>

    <div class="modal-field">
      <div class="modal-field-lbl">Post URL</div>
      <div class="modal-field-val">
        <a href="${escHtml(lead.post_url || '#')}" target="_blank" style="color:#60a5fa;word-break:break-all">
          ${escHtml((lead.post_url || 'N/A').slice(0, 60))}…
        </a>
      </div>
    </div>

    <div class="modal-field">
      <div class="modal-field-lbl">Update Status</div>
      <select class="status-select" id="statusSelect">
        ${['new','contacted','follow-up','converted'].map(s =>
          `<option value="${s}" ${lead.status === s ? 'selected' : ''}>${s}</option>`
        ).join('')}
      </select>
    </div>

    <div style="display:flex;gap:6px;margin-top:8px">
      <button id="modalSaveStatus" style="flex:1;padding:7px;background:#D4AF37;border:none;border-radius:6px;color:#0D1117;font-weight:700;cursor:pointer;font-size:12px">
        💾 Save Status
      </button>
      <a href="${waUrl}" target="_blank" style="flex:1;display:flex;align-items:center;justify-content:center;padding:7px;background:#22c55e;border-radius:6px;color:white;font-weight:700;font-size:12px;text-decoration:none">
        💬 WhatsApp
      </a>
    </div>
    <button class="modal-close" id="modalClose">✕ Close</button>
  `;

  modalOverlay.classList.add('open');

  $('modalClose').addEventListener('click', () => modalOverlay.classList.remove('open'));
  modalOverlay.addEventListener('click', (e) => { if (e.target === modalOverlay) modalOverlay.classList.remove('open'); });

  $('modalSaveStatus').addEventListener('click', async () => {
    const newStatus = $('statusSelect').value;
    const res = await send('UPDATE_STATUS', { id: lead.id, status: newStatus });
    if (res.success) {
      $('modalSaveStatus').textContent = '✅ Saved!';
      setTimeout(() => loadLeads(), 400);
    } else {
      $('modalSaveStatus').textContent = '❌ Failed';
    }
  });
}

// ── XSS helper ────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Init ───────────────────────────────────────────────────────
async function init() {
  // Load saved URL
  const stored = await new Promise(r => chrome.storage.local.get(['backendUrl'], r));
  if (stored.backendUrl) {
    backendUrl = stored.backendUrl;
    backendUrlInput.value = backendUrl;
  } else {
    backendUrlInput.value = DEFAULT_URL;
  }

  await checkHealth();
  await loadLeads();
}

// ── Event listeners ────────────────────────────────────────────
$('refreshBtn').addEventListener('click', async () => {
  await checkHealth();
  await loadLeads();
});

$('settingsToggle').addEventListener('click', () => {
  $('settingsPanel').classList.toggle('open');
});

$('saveUrlBtn').addEventListener('click', async () => {
  const val = backendUrlInput.value.trim().replace(/\/$/, '');
  if (!val) return;
  backendUrl = val;
  await chrome.storage.local.set({ backendUrl: val });
  settingsHint.textContent = '✅ Saved! Reconnecting…';
  settingsHint.style.color = '#22c55e';
  await checkHealth();
  await loadLeads();
  settingsHint.textContent = 'Enter your backend server URL';
  settingsHint.style.color = '';
});

$('openFbBtn').addEventListener('click', () => {
  chrome.tabs.create({ url: 'https://www.facebook.com' });
});

$('openDashBtn').addEventListener('click', () => {
  chrome.tabs.create({ url: `${backendUrl}/dashboard` });
});

// ── Start ──────────────────────────────────────────────────────
init();
