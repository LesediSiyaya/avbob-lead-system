// ============================================================
//  AVBOB Lead Assistant — content_script.js
//  Runs on Facebook. Detects high-intent posts, injects UI.
// ============================================================
'use strict';

// ── Keywords in all 11 SA official languages ─────────────────
const KEYWORDS = [
  // English
  'funeral cover','burial policy','funeral plan','funeral insurance',
  'burial society','death cover','funeral costs','passed away',
  'life cover','final expenses','avbob','burial cover',
  // isiZulu
  'umngcwabo','indleko zomngcwabo','umhlangano wokungcwaba','umuntu oshonile',
  // isiXhosa
  'amatyala omngcwabo','umntu oswelekileyo','umgcwabo',
  // Afrikaans
  'begrafnisdekking','begrafnispolis','begrafnis','oorlede',
  // Sesotho
  'polokelo ya mofu','ditshenyehelo tsa poloko','mofu',
  // Setswana
  'poloko ya mohu','go fitlhwa','mohu',
  // Sepedi
  'ditshenyegelo tsha poloko','motho yo a hwilego',
  // Xitsonga
  'ku famba','mihlawulelo ya ku lahla',
];

// ── State ──────────────────────────────────────────────────────
const injectedPosts = new WeakSet();
let backendUrl = 'http://localhost:8000';

// Load backend URL from storage
chrome.storage.local.get(['backendUrl'], (r) => {
  if (r.backendUrl) backendUrl = r.backendUrl;
});
chrome.storage.onChanged.addListener((changes) => {
  if (changes.backendUrl) backendUrl = changes.backendUrl.newValue;
});

// ── Keyword detection ──────────────────────────────────────────
function matchesKeyword(text) {
  const lower = text.toLowerCase();
  return KEYWORDS.filter(kw => lower.includes(kw));
}

// ── Extract post data from a Facebook article element ─────────
function extractPost(el) {
  // --- Text (multiple fallback strategies) ---
  let text = '';
  const textCandidates = [
    el.querySelector('[data-ad-comet-preview="message"]'),
    el.querySelector('[data-ad-preview="message"]'),
    el.querySelector('[data-testid="post_message"]'),
    el.querySelector('div[dir="auto"][style*="text-align"]'),
    el.querySelector('div[class*="userContent"]'),
  ];
  for (const c of textCandidates) {
    if (c && c.innerText.trim().length > 15) {
      text = c.innerText.trim();
      break;
    }
  }
  if (!text) {
    // Last resort: grab all visible text from the article, strip UI chrome
    const clone = el.cloneNode(true);
    clone.querySelectorAll('button, svg, [role="button"]').forEach(n => n.remove());
    text = (clone.innerText || '').trim().slice(0, 1200);
  }

  // --- Author ---
  let author = 'Unknown';
  const authorCandidates = [
    el.querySelector('strong > span'),
    el.querySelector('h3 span a span'),
    el.querySelector('h2 a span'),
    el.querySelector('a[role="link"] > span > span'),
  ];
  for (const c of authorCandidates) {
    if (c && c.innerText.trim().length > 1) {
      author = c.innerText.trim();
      break;
    }
  }

  // --- Post URL ---
  let postUrl = window.location.href;
  const linkCandidates = [
    el.querySelector('a[href*="/groups/"][href*="/posts/"]'),
    el.querySelector('a[href*="story_fbid"]'),
    el.querySelector('a[href*="/permalink/"]'),
    el.querySelector('a[href*="?p="]'),
  ];
  for (const c of linkCandidates) {
    if (c && c.href) { postUrl = c.href; break; }
  }

  return { text, author, postUrl };
}

// ── Score badge colour ─────────────────────────────────────────
function scoreColour(score) {
  if (score >= 75) return { bg: '#dcfce7', text: '#166534', border: '#22c55e' };
  if (score >= 45) return { bg: '#fef9c3', text: '#854d0e', border: '#eab308' };
  return          { bg: '#fee2e2', text: '#991b1b', border: '#ef4444' };
}

// ── Build the injected toolbar HTML ───────────────────────────
function buildToolbar(postData) {
  const wrap = document.createElement('div');
  wrap.className = 'avbob-wrap';

  wrap.innerHTML = `
    <div class="avbob-bar">
      <span class="avbob-logo">🤝 AVBOB Lead Detected</span>
      <div class="avbob-btns">
        <button class="avbob-btn" data-action="analyze">🤖 Analyze</button>
        <button class="avbob-btn" data-action="reply">✍️ Reply</button>
        <button class="avbob-btn" data-action="whatsapp">💬 WhatsApp</button>
        <button class="avbob-btn avbob-save" data-action="save">💾 Save</button>
      </div>
    </div>
    <div class="avbob-panel"></div>
  `;

  const panel  = wrap.querySelector('.avbob-panel');
  const savBtn = wrap.querySelector('[data-action="save"]');

  function showLoading(msg) {
    panel.style.display = 'block';
    panel.innerHTML = `<div class="avbob-loading"><span class="avbob-spinner"></span>${msg}</div>`;
  }

  function showError(msg) {
    panel.innerHTML = `<div class="avbob-error">❌ ${msg}</div>`;
  }

  // ── ANALYZE ──────────────────────────────────────────────────
  wrap.querySelector('[data-action="analyze"]').addEventListener('click', async () => {
    showLoading('Analyzing lead with AI…');
    const res = await sendToBackground('ANALYZE_LEAD', postData);
    if (!res.success) { showError(res.error); return; }

    const { score, intent, summary, matched_keywords, language } = res.data;
    const col = scoreColour(score);

    panel.innerHTML = `
      <div class="avbob-result">
        <div class="avbob-score-row">
          <div class="avbob-score" style="background:${col.bg};color:${col.text};border-color:${col.border}">
            ${score}<small>/100</small>
          </div>
          <div class="avbob-intent avbob-intent-${intent.toLowerCase()}">${intent.toUpperCase()} INTENT</div>
          ${language !== 'en' ? `<div class="avbob-lang">🌍 ${language}</div>` : ''}
        </div>
        <div class="avbob-summary">${summary}</div>
        <div class="avbob-keywords">
          ${(matched_keywords || []).map(k => `<span class="avbob-kw">${k}</span>`).join('')}
        </div>
      </div>`;
  });

  // ── REPLY ─────────────────────────────────────────────────────
  wrap.querySelector('[data-action="reply"]').addEventListener('click', async () => {
    showLoading('Generating AI reply…');
    const res = await sendToBackground('GENERATE_REPLY', postData);
    if (!res.success) { showError(res.error); return; }

    const { reply } = res.data;
    const id = 'avbob-reply-' + Date.now();
    panel.innerHTML = `
      <div class="avbob-result">
        <div class="avbob-label">💬 Suggested Reply</div>
        <div class="avbob-reply-box" id="${id}">${reply}</div>
        <div class="avbob-actions">
          <button class="avbob-copy-btn" id="copy-${id}">📋 Copy</button>
          <span class="avbob-note">Review before posting. Never auto-send.</span>
        </div>
      </div>`;

    document.getElementById('copy-' + id).addEventListener('click', function () {
      navigator.clipboard.writeText(document.getElementById(id).innerText);
      this.textContent = '✓ Copied!';
      setTimeout(() => (this.textContent = '📋 Copy'), 2000);
    });
  });

  // ── WHATSAPP ──────────────────────────────────────────────────
  wrap.querySelector('[data-action="whatsapp"]').addEventListener('click', async () => {
    showLoading('Generating WhatsApp follow-up…');
    const res = await sendToBackground('WHATSAPP_LINK', postData);
    if (!res.success) { showError(res.error); return; }

    const { message, link, phone_prompt } = res.data;
    const msgId = 'avbob-wa-' + Date.now();
    panel.innerHTML = `
      <div class="avbob-result">
        <div class="avbob-label">💬 WhatsApp Follow-up</div>
        <div class="avbob-reply-box" id="${msgId}">${message}</div>
        <div class="avbob-actions">
          <a class="avbob-wa-btn" href="${link}" target="_blank" rel="noopener">Open WhatsApp</a>
          <button class="avbob-copy-btn" id="copy-${msgId}">📋 Copy Message</button>
        </div>
        <div class="avbob-note">⚠️ ${phone_prompt}</div>
      </div>`;

    document.getElementById('copy-' + msgId).addEventListener('click', function () {
      navigator.clipboard.writeText(document.getElementById(msgId).innerText);
      this.textContent = '✓ Copied!';
      setTimeout(() => (this.textContent = '📋 Copy Message'), 2000);
    });
  });

  // ── SAVE ──────────────────────────────────────────────────────
  savBtn.addEventListener('click', async () => {
    if (savBtn.dataset.saved === 'true') return;
    savBtn.textContent = '⏳ Saving…';
    savBtn.disabled = true;

    const res = await sendToBackground('SAVE_LEAD', postData);
    if (res.success) {
      savBtn.textContent = '✅ Saved';
      savBtn.dataset.saved = 'true';
      savBtn.style.background = '#22c55e';
    } else {
      savBtn.textContent = '❌ Failed';
      savBtn.disabled = false;
      showError(res.error || 'Could not save lead. Is the backend running?');
    }
  });

  return wrap;
}

// ── Send a message to background.js ───────────────────────────
function sendToBackground(type, data) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type, data, backendUrl }, (res) => {
      if (chrome.runtime.lastError) {
        resolve({ success: false, error: chrome.runtime.lastError.message });
      } else {
        resolve(res || { success: false, error: 'No response from background' });
      }
    });
  });
}

// ── Process a single [role="article"] element ─────────────────
function processArticle(article) {
  if (injectedPosts.has(article)) return;

  const { text, author, postUrl } = extractPost(article);
  if (!text || text.length < 20) return;

  const hits = matchesKeyword(text);
  if (hits.length === 0) return;

  injectedPosts.add(article);
  article.classList.add('avbob-detected-post');

  const toolbar = buildToolbar({ text, author, postUrl, matched_keywords: hits });

  // Inject after the post text area, before the reaction bar
  const footer = article.querySelector('[aria-label*="reactions"]')?.closest('div')
    ?? article.querySelector('[data-testid="UFI2CommentsCount"]')?.closest('div')
    ?? article;

  try { footer.parentNode.insertBefore(toolbar, footer); }
  catch { article.appendChild(toolbar); }
}

// ── Scan all visible articles ─────────────────────────────────
function scanAll() {
  document.querySelectorAll('[role="article"]').forEach(processArticle);
}

// ── MutationObserver: watch for new posts ─────────────────────
let scanTimer = null;
const observer = new MutationObserver(() => {
  clearTimeout(scanTimer);
  scanTimer = setTimeout(scanAll, 600);
});

observer.observe(document.body, { childList: true, subtree: true });

// Initial scan after FB finishes loading
setTimeout(scanAll, 2500);
setTimeout(scanAll, 5000); // second pass for slow connections
