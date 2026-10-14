/* ══════════════════════════════════════════════════════════════════════════ */
/* TADABBUR — Reflect. Understand. Remember.                                 */
/* ══════════════════════════════════════════════════════════════════════════ */

/* ── API client ──────────────────────────────────────────────────────────── */
let _apiCache = {};
const _videoCache = new Map();
const API = {
  async request(method, path, body = null, cacheSeconds = 0) {
    const cacheKey = method + path;
    if (method !== 'GET') { _apiCache = {}; }
    if (method === 'GET' && cacheSeconds > 0 && _apiCache[cacheKey] && (Date.now() - _apiCache[cacheKey].ts < cacheSeconds * 1000)) {
      return _apiCache[cacheKey].data;
    }
    const opts = { method, credentials: 'same-origin', headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`/api/v1${path}`, opts);
    const ct = res.headers.get('content-type') || '';
    const data = ct.includes('application/json') ? await res.json() : null;
    if (!res.ok) {
      let msg = data?.detail || data?.error?.message;
      if (Array.isArray(msg)) { msg = msg.map(e => e.msg || JSON.stringify(e)).join(', '); }
      else if (msg && typeof msg === 'object') { msg = JSON.stringify(msg); }
      if (!msg) { msg = res.status >= 500 ? 'An unexpected server error occurred. Please try again later.' : `Error (HTTP ${res.status})`; }
      throw Object.assign(new Error(msg), { status: res.status, data });
    }
    return data;
  },
  get:    (p, cache = 0) => API.request('GET',    p, null, cache),
  post:   (p, b) => API.request('POST',   p, b),
  patch:  (p, b) => API.request('PATCH',  p, b),
  delete: (p)    => API.request('DELETE', p),
};

/* ── Video blob cache ──────────────────────────────────────────────────── */
async function cacheVideoBlob(videoId) {
  if (_videoCache.has(videoId)) return true;
  try {
    const resp = await fetch(`/api/v1/videos/${videoId}/stream`, { credentials: 'same-origin' });
    if (!resp.ok) return false;
    const blob = await resp.blob();
    _videoCache.set(videoId, blob);
    return true;
  } catch { return false; }
}

/* ── Static Data: Du'as ────────────────────────────────────────────────── */
const DUAS = [
  {
    id: 'sleeping',
    title: "Du'a Before Sleeping",
    arabic: 'بِاسْمِكَ اللَّهُمَّ أَمُوتُ وَأَحْيَا',
    translation: 'In Your name, O Allah, I die and I live.',
    category: 'Sleep',
    icon: '🌙',
  },
  {
    id: 'waking',
    title: "Du'a Upon Waking Up",
    arabic: 'الْحَمْدُ لِلَّهِ الَّذِي أَحْيَانَا بَعْدَ مَا أَمَاتَنَا وَإِلَيْهِ النُّشُورُ',
    translation: 'All praise is for Allah who gave us life after having taken it from us and unto Him is the resurrection.',
    category: 'Morning',
    icon: '🌅',
  },
  {
    id: 'eating',
    title: "Du'a Before Eating",
    arabic: 'بِسْمِ اللَّهِ',
    translation: 'In the name of Allah.',
    category: 'Eating',
    icon: '🍽️',
  },
];

/* ── Static Data: Verses ───────────────────────────────────────────────── */
const VERSES = [
  { arabic: 'رَبِّ زِدْنِي عِلْمًا', translation: 'My Lord, increase me in knowledge.', ref: "Qur'an 20:114" },
  { arabic: 'إِنَّ مَعَ الْعُسْرِ يُسْرًا', translation: 'Indeed, with hardship comes ease.', ref: "Qur'an 94:6" },
  { arabic: 'فَاذْكُرُونِي أَذْكُرْكُمْ', translation: 'So remember Me; I will remember you.', ref: "Qur'an 2:152" },
];

function todayVerse() {
  const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0)) / 86400000);
  return VERSES[dayOfYear % VERSES.length];
}

function todayDua() {
  const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0)) / 86400000);
  return DUAS[dayOfYear % DUAS.length];
}

/* ── Saved/Bookmarks (localStorage) ────────────────────────────────────── */
function getSaved() {
  try { return JSON.parse(localStorage.getItem('tadabbur_saved') || '[]'); } catch { return []; }
}
function setSaved(items) { localStorage.setItem('tadabbur_saved', JSON.stringify(items)); }
function isSaved(type, id) { return getSaved().some(s => s.type === type && s.id === id); }
function toggleSaved(type, id, title) {
  const saved = getSaved();
  const idx = saved.findIndex(s => s.type === type && s.id === id);
  if (idx >= 0) saved.splice(idx, 1);
  else saved.push({ type, id, title });
  setSaved(saved);
  return idx < 0;
}

/* ── Settings (localStorage) ───────────────────────────────────────────── */
function getSettings() {
  try { return JSON.parse(localStorage.getItem('tadabbur_settings') || '{}'); } catch { return {}; }
}
function setSettings(s) { localStorage.setItem('tadabbur_settings', JSON.stringify(s)); }

/* ── Router ────────────────────────────────────────────────────────────── */
const ROUTES = {
  '/':       renderSplash,
  '/home':   renderHome,
  '/videos': renderVideos,
  '/duas':   renderDuas,
  '/saved':  renderSaved,
  '/settings': renderSettings,
  '/dashboard': renderHome,
  '/library':  renderVideos,
  '/activate': renderActivate,
  '/history':  renderHistory,
  '/progress': renderProgress,
  '/profile':  renderProfile,
  '/admin':    renderAdmin,
};

let _currentUser = null;

async function getUser() {
  if (_currentUser) return _currentUser;
  try { _currentUser = await API.get('/auth/me'); return _currentUser; }
  catch { return null; }
}
function clearUser() { _currentUser = null; }
function navigate(path) { window.location.hash = path; }

async function route() {
  const hash = window.location.hash.slice(1) || '/';
  const handler = ROUTES[hash] || renderSplash;
  const app = document.getElementById('app');
  try { await handler(app); }
  catch (e) {
    console.error(e);
    app.innerHTML = `<div class="page"><div class="empty-state"><p>${escHtml(e.message)}</p><a href="#/home" class="btn btn-primary">Go Home</a></div></div>`;
  }
}
window.addEventListener('hashchange', route);
window.addEventListener('DOMContentLoaded', route);

/* ── Helpers ───────────────────────────────────────────────────────────── */
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function fmtDuration(secs) {
  if (!secs) return '';
  const m = Math.floor(secs / 60), s = secs % 60;
  return `${m}:${String(s).padStart(2,'0')}`;
}

/* ── Navigation ────────────────────────────────────────────────────────── */
function navHtml(active) {
  const items = [
    { href: '#/home',    icon: 'home',          label: 'Home' },
    { href: '#/videos',  icon: 'movie',         label: 'Videos' },
    { href: '#/duas',    icon: 'self_improvement', label: "Du'as" },
    { href: '#/saved',   icon: 'bookmark',      label: 'Saved' },
  ];
  const links = items.map(i => `
    <a href="${i.href}" class="nav-item ${active === i.href ? 'active' : ''}">
      <span class="nav-icon material-symbols-outlined">${i.icon}</span>
      <span>${i.label}</span>
    </a>
  `).join('');
  return `<nav class="bottom-nav">${links}</nav>`;
}

function bindLogout() {
  document.querySelectorAll('[data-logout]').forEach(el => {
    el.addEventListener('click', async () => {
      try { await API.post('/auth/logout'); } catch {}
      clearUser();
      navigate('/');
    });
  });
}

/* ── Splash Screen ─────────────────────────────────────────────────────── */
async function renderSplash(app) {
  const user = await getUser();
  if (user) { navigate('/home'); return; }
  app.innerHTML = `
    <div class="splash">
      <svg class="splash-logo" viewBox="0 0 120 120" fill="none">
        <path d="M60 25c-8-10-22-14-35-14v70c13 0 27 4 35 14 8-10 22-14 35-14V11c-13 0-27 4-35 14z" fill="currentColor" opacity="0.9"/>
        <path d="M60 25v70" stroke="white" stroke-width="2"/>
        <path d="M25 11v70c13 0 27 4 35 14V25c-8-10-22-14-35-14z" fill="currentColor" opacity="0.7"/>
        <path d="M95 11v70c-13 0-27-4-35-14V25c8-10 22-14 35-14z" fill="currentColor" opacity="0.7"/>
      </svg>
      <div class="splash-brand">TADABBUR</div>
      <p class="splash-tagline">Reflect. Understand. Remember.</p>
      <div class="splash-divider"></div>
      <a href="#/activate" class="btn btn-primary splash-btn">Get Started</a>
      <div class="splash-dots">
        <div class="splash-dot"></div>
        <div class="splash-dot inactive"></div>
        <div class="splash-dot inactive"></div>
      </div>
    </div>`;
}

/* ── Activation ────────────────────────────────────────────────────────── */
async function renderActivate(app) {
  const user = await getUser();
  if (user) { navigate('/home'); return; }
  app.innerHTML = `
    <div class="page" style="display:flex;align-items:center;justify-content:center;min-height:100dvh;">
      <div style="width:100%;max-width:400px;text-align:center;">
        <div style="font-size:1.5rem;font-weight:800;color:var(--color-primary);margin-bottom:8px;">TADABBUR</div>
        <p style="color:var(--color-muted);margin-bottom:24px;">Enter your name to activate your profile.</p>
        <form id="activate-form">
          <input id="name" type="text" required placeholder="Your name" maxlength="100"
            style="width:100%;padding:14px 20px;border:1.5px solid var(--color-border);border-radius:9999px;font-size:1rem;margin-bottom:16px;text-align:center;" />
          <button type="submit" class="btn btn-primary btn-block">Continue</button>
        </form>
      </div>
    </div>`;
  app.querySelector('#activate-form').addEventListener('submit', async e => {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    btn.disabled = true;
    const name = app.querySelector('#name').value.trim();
    if (!name) { btn.disabled = false; return; }
    try {
      await API.post('/auth/activate', { name });
      clearUser();
      _currentUser = await getUser();
      navigate('/home');
    } catch (err) {
      alert(err.message);
      btn.disabled = false;
    }
  });
}

/* ── Home Screen ───────────────────────────────────────────────────────── */
async function renderHome(app) {
  const user = await getUser();
  if (!user) { navigate('/'); return; }
  app.innerHTML = `${navHtml('#/home')}<div class="page" id="home-content"><div class="empty-state"><p>Loading...</p></div></div>`;

  try {
    const video = await API.get('/reminders/today');
    const verse = todayVerse();
    const isVideoSaved = isSaved('video', video.id);
    app.querySelector('#home-content').innerHTML = `
      <div class="page-header">
        <span class="brand">TADABBUR</span>
        <a href="#/settings" class="icon-btn material-symbols-outlined">menu</a>
      </div>
      <h1 class="greeting">Assalamu Alaikum</h1>
      <p class="greeting-sub">Take a moment to reflect.</p>
      <div class="section-title">TODAY'S REMINDER</div>
      <div class="reminder-card">
        <video class="reminder-video" src="/api/v1/videos/${video.id}/stream" controls preload="metadata"></video>
        <div class="reminder-body">
          <div class="reminder-title">${escHtml(video.title)}</div>
          ${video.description ? `<p class="reminder-desc">${escHtml(video.description)}</p>` : ''}
          <div class="reminder-actions">
            <a href="#/videos" class="watch-link">▶ Watch Reminder</a>
            <button class="btn btn-primary btn-sm" onclick="shareVideoFile(${video.id}, '${escHtml(video.title).replace(/'/g, "\\'")}')">Share to WhatsApp</button>
          </div>
        </div>
      </div>
      <div class="section-title">QUR'AN VERSE OF THE DAY</div>
      <div class="verse-card">
        <div class="verse-arabic">${verse.arabic}</div>
        <div class="verse-translation">${verse.translation}</div>
        <div class="verse-ref">${verse.ref}</div>
        <a href="#/videos" class="verse-link">Read & Reflect →</a>
      </div>`;
  } catch (e) {
    app.querySelector('#home-content').innerHTML = `<div class="empty-state"><p>${escHtml(e.message)}</p></div>`;
  }
}

/* ── Videos Screen ─────────────────────────────────────────────────────── */
let _videoSearch = '';
let _videoCategory = 'All';

async function renderVideos(app) {
  const user = await getUser();
  if (!user) { navigate('/'); return; }
  app.innerHTML = `${navHtml('#/videos')}<div class="page" id="videos-content"><div class="empty-state"><p>Loading...</p></div></div>`;

  const categories = ['All', "Qur'an", "Du'a", 'Akhirah', 'More'];

  async function loadVideos() {
    const el = app.querySelector('#videos-content');
    if (!el) return;
    try {
      const qs = new URLSearchParams({ skip: 0, limit: 100 });
      if (_videoSearch) qs.set('search', _videoSearch);
      const res = await API.get('/videos?' + qs.toString(), 60);
      let items = res.items || [];
      if (_videoCategory !== 'All') items = items.filter(v => (v.title || '').toLowerCase().includes(_videoCategory.toLowerCase()));

      const cards = items.map(v => `
        <div class="video-card">
          <div class="video-thumb">
            <div class="play-icon material-symbols-outlined">play_arrow</div>
          </div>
          <div class="video-info">
            <div class="video-title">${escHtml(v.title)}</div>
            ${v.description ? `<div class="video-desc">${escHtml(v.description)}</div>` : ''}
            ${v.duration_seconds ? `<div class="video-duration">Duration: ${fmtDuration(v.duration_seconds)}</div>` : ''}
            <div class="video-actions">
              <button class="btn btn-primary btn-sm" onclick="watchVideo(${v.id})">▶ Watch Reminder</button>
              <button class="btn btn-primary btn-sm" onclick="shareVideoFile(${v.id}, '${escHtml(v.title).replace(/'/g, "\\'")}')">Share to WhatsApp</button>
            </div>
          </div>
        </div>
      `).join('');

      el.innerHTML = `
        <div class="page-header">
          <span class="brand">TADABBUR</span>
        </div>
        <h1 class="page-title">Islamic Video Reminders</h1>
        <p class="page-subtitle">Short reminders, Lasting reflections.</p>
        <div class="search-wrap">
          <span class="search-icon material-symbols-outlined">search</span>
          <input id="video-search" class="search-input" type="text" placeholder="Search Reminders..." value="${escHtml(_videoSearch)}" />
        </div>
        <div class="pill-row">
          ${categories.map(c => `<button class="pill ${_videoCategory === c ? 'active' : ''}" onclick="setVideoCategory('${c}')">${c}</button>`).join('')}
        </div>
        <div id="video-list">${cards || '<div class="empty-state"><p>No videos found.</p></div>'}</div>`;

      const searchInput = el.querySelector('#video-search');
      let searchTimer;
      searchInput.addEventListener('input', e => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => { _videoSearch = e.target.value.trim(); loadVideos(); }, 350);
      });
    } catch (e) {
      el.innerHTML = `<div class="empty-state"><p>${escHtml(e.message)}</p></div>`;
    }
  }

  loadVideos();
}

function setVideoCategory(cat) { _videoCategory = cat; renderVideos(document.getElementById('app')); }

/* ── Du'as Screen ──────────────────────────────────────────────────────── */
let _duaCategory = 'All';
let _duaSearch = '';

async function renderDuas(app) {
  const user = await getUser();
  if (!user) { navigate('/'); return; }
  app.innerHTML = `${navHtml('#/duas')}<div class="page" id="duas-content"><div class="empty-state"><p>Loading...</p></div></div>`;

  const categories = ['All', 'Morning', 'Evening', 'Sleep', 'More'];
  let activeCat = _duaCategory;
  let searchQ = _duaSearch;

  const duaOfDay = todayDua();
  const moreDuas = DUAS.filter(d => d.id !== duaOfDay.id);

  function renderList() {
    const el = app.querySelector('#duas-content');
    if (!el) return;
    let filtered = DUAS;
    if (activeCat !== 'All') filtered = filtered.filter(d => d.category === activeCat);
    if (searchQ) filtered = filtered.filter(d => d.title.toLowerCase().includes(searchQ.toLowerCase()));

    el.innerHTML = `
      <div class="page-header">
        <span class="brand">TADABBUR</span>
      </div>
      <h1 class="page-title">Daily Du'as</h1>
      <p class="page-subtitle">Supplications For Everyday</p>
      <div class="search-wrap">
        <span class="search-icon material-symbols-outlined">search</span>
        <input id="dua-search" class="search-input" type="text" placeholder="Search du'as..." value="${escHtml(searchQ)}" />
      </div>
      <div class="pill-row">
        ${categories.map(c => `<button class="pill ${activeCat === c ? 'active' : ''}" onclick="setDuaCategory('${c}')">${c}</button>`).join('')}
      </div>
      <div class="section-title">DU'A OF THE DAY</div>
      <div class="dua-card">
        <div class="dua-arabic">${duaOfDay.arabic}</div>
        <div class="dua-translation">${duaOfDay.translation}</div>
        <div class="dua-actions">
          <button class="btn btn-primary btn-sm">Read Du'a →</button>
          <button class="btn btn-outline btn-sm" onclick="toggleSaved('dua', '${duaOfDay.id}', '${escHtml(duaOfDay.title).replace(/'/g, "\\'")}'); renderDuas(document.getElementById('app'));">Save</button>
        </div>
      </div>
      <div class="section-title">MORE DAILY DU'AS</div>
      ${moreDuas.map(d => `
        <div class="dua-list-card">
          <div class="dua-icon">${d.icon}</div>
          <div class="dua-list-info">
            <div class="dua-list-title">${d.title}</div>
            <div class="dua-list-sub">${d.category}</div>
          </div>
          <span class="dua-arrow">→</span>
        </div>
      `).join('')}
    `;

    const searchInput = el.querySelector('#dua-search');
    let searchTimer;
    searchInput.addEventListener('input', e => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => { _duaSearch = e.target.value.trim(); activeCat = _duaCategory; renderList(); }, 350);
    });
  }

  renderList();
}

function setDuaCategory(cat) { _duaCategory = cat; _duaSearch = ''; renderDuas(document.getElementById('app')); }

/* ── Saved Screen ──────────────────────────────────────────────────────── */
async function renderSaved(app) {
  const user = await getUser();
  if (!user) { navigate('/'); return; }
  app.innerHTML = `${navHtml('#/saved')}<div class="page" id="saved-content"><div class="empty-state"><p>Loading...</p></div></div>`;

  const saved = getSaved();
  const videoItems = saved.filter(s => s.type === 'video');
  const duaItems = saved.filter(s => s.type === 'dua');
  const duaMap = Object.fromEntries(DUAS.map(d => [d.id, d]));

  function renderList() {
    const el = app.querySelector('#saved-content');
    if (!el) return;

    const videoCards = videoItems.map(s => `
      <div class="saved-video-card">
        <div class="saved-thumb">
          <div class="play-overlay material-symbols-outlined">play_arrow</div>
        </div>
        <div class="saved-info">
          <div class="saved-title">${escHtml(s.title)}</div>
          <div class="saved-meta">Video Reminder</div>
          <div class="saved-actions">
            <button class="btn btn-primary btn-sm" onclick="watchVideo(${s.id})">Watch Reminder</button>
            <button class="bookmark-btn" onclick="toggleSaved('video', ${s.id}); renderSaved(document.getElementById('app'));" title="Remove">★</button>
          </div>
        </div>
      </div>
    `).join('');

    const duaCards = duaItems.map(s => {
      const d = duaMap[s.id] || { title: s.title, icon: '📖' };
      return `
        <div class="dua-list-card">
          <div class="dua-icon">${d.icon}</div>
          <div class="dua-list-info">
            <div class="dua-list-title">${escHtml(d.title)}</div>
          </div>
          <button class="bookmark-btn" onclick="toggleSaved('dua', '${s.id}'); renderSaved(document.getElementById('app'));" title="Remove">★</button>
        </div>
      `;
    }).join('');

    el.innerHTML = `
      <div class="page-header">
        <span class="brand">TADABBUR</span>
      </div>
      <h1 class="page-title">Your Saved Reminders</h1>
      <p class="page-subtitle">Keep the reminders that matter to you.</p>
      <div class="pill-row">
        <button class="pill active">All</button>
        <button class="pill">Videos</button>
        <button class="pill">Du'as</button>
      </div>
      ${videoItems.length === 0 && duaItems.length === 0 ? `
        <div class="empty-state">
          <div class="empty-icon">📖</div>
          <p>No saved reminders yet.</p>
          <p style="font-size:0.8rem;margin-top:4px;">Bookmark videos and du'as to see them here.</p>
        </div>
      ` : `
        ${videoItems.length > 0 ? `<div class="section-title">SAVED VIDEOS</div>${videoCards}` : ''}
        ${duaItems.length > 0 ? `<div class="section-title">SAVED DU'AS</div>${duaCards}` : ''}
      `}
    `;
  }

  renderList();
}

/* ── Settings Screen ────────────────────────────────────────────────────── */
async function renderSettings(app) {
  const user = await getUser();
  if (!user) { navigate('/'); return; }
  const settings = getSettings();
  app.innerHTML = `${navHtml('')}<div class="page" id="settings-content"></div>`;

  function renderSettings() {
    const el = app.querySelector('#settings-content');
    if (!el) return;
    el.innerHTML = `
      <div class="page-header">
        <span class="brand">TADABBUR</span>
        <a href="#/settings" class="icon-btn material-symbols-outlined">settings</a>
      </div>
      <h1 class="page-title">Notification & Reminders</h1>
      <p class="page-subtitle">Stay connected to daily reminders.</p>
      <div class="section-title">DAILY REMINDERS</div>
      <div class="settings-card">
        <div class="settings-icon material-symbols-outlined">notifications</div>
        <div class="settings-info">
          <div class="settings-label">Daily Qur'an Reminder</div>
          <div class="settings-desc">Receive a short reminder everyday.</div>
        </div>
        <button class="toggle ${settings.quranReminder ? 'active' : ''}" onclick="toggleSetting('quranReminder')" aria-label="Toggle"></button>
      </div>
      <div class="settings-card">
        <div class="settings-icon material-symbols-outlined">schedule</div>
        <div class="settings-info">
          <div class="settings-label">Reminder time</div>
        </div>
        <span style="font-weight:700;color:var(--color-text);">7:00 AM ›</span>
      </div>
      <div class="settings-card">
        <div class="settings-icon material-symbols-outlined">hands</div>
        <div class="settings-info">
          <div class="settings-label">Daily Du'a</div>
          <div class="settings-desc">A daily supplication to reflect on.</div>
        </div>
        <button class="toggle ${settings.duaReminder ? 'active' : ''}" onclick="toggleSetting('duaReminder')" aria-label="Toggle"></button>
      </div>
      <div class="section-title">LANGUAGE PREFERENCES</div>
      <div class="card-flat" style="display:flex;gap:12px;">
        <button class="lang-btn active">English</button>
        <button class="lang-btn">العربية</button>
      </div>
      <div class="section-title">CONTACT US</div>
      <div class="settings-card">
        <div class="settings-icon material-symbols-outlined">chat</div>
        <div class="settings-info">
          <div class="settings-label">Contact Support</div>
          <div class="settings-desc">Reach out for help or to provide feedback.</div>
        </div>
        <span style="color:var(--color-primary);font-weight:700;">›</span>
      </div>
    `;
  }

  renderSettings();
}

function toggleSetting(key) {
  const settings = getSettings();
  settings[key] = !settings[key];
  setSettings(settings);
  renderSettings(document.getElementById('app'));
}

/* ── Video Modal ───────────────────────────────────────────────────────── */
function watchVideo(videoId) {
  cacheVideoBlob(videoId);
  const existing = document.getElementById('video-modal');
  if (existing) existing.remove();

  const modal = document.createElement('div');
  modal.id = 'video-modal';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:200;display:flex;align-items:center;justify-content:center;padding:16px;';
  modal.innerHTML = `
    <div style="background:var(--color-card);border-radius:20px;max-width:480px;width:100%;overflow:hidden;position:relative;">
      <button onclick="document.getElementById('video-modal').remove()" style="position:absolute;top:12px;right:12px;z-index:10;background:rgba(0,0,0,.5);color:#fff;border:none;border-radius:50%;width:36px;height:36px;font-size:1.2rem;cursor:pointer;">✕</button>
      <video id="modal-video" controls autoplay style="width:100%;max-height:70vh;background:#000;" src="/api/v1/videos/${videoId}/stream"></video>
      <div id="modal-video-info" style="padding:16px;"></div>
    </div>`;
  document.body.appendChild(modal);
  modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });

  // Load video info
  API.get(`/videos/${videoId}`).then(v => {
    const info = document.getElementById('modal-video-info');
    if (info) {
      info.innerHTML = `
        <div style="font-weight:800;font-size:1.1rem;margin-bottom:4px;">${escHtml(v.title)}</div>
        ${v.description ? `<div style="font-size:.85rem;color:var(--color-muted);margin-bottom:12px;">${escHtml(v.description)}</div>` : ''}
        ${v.duration_seconds ? `<div style="font-size:.8rem;color:var(--color-muted);">Duration: ${fmtDuration(v.duration_seconds)}</div>` : ''}
        <button class="btn btn-primary btn-sm" style="margin-top:12px;width:100%;" onclick="shareVideoFile(${v.id}, '${escHtml(v.title).replace(/'/g, "\\'")}'); document.getElementById('video-modal').remove();">Share to WhatsApp</button>
      `;
    }
  }).catch(() => {});
}

/* ── Share ─────────────────────────────────────────────────────────────── */
async function shareVideoFile(videoId, title) {
  const cachedBlob = _videoCache.get(videoId);
  if (!cachedBlob) return false;
  const safeTitle = (title || 'reminder').replace(/[^a-zA-Z0-9]/g, '_');
  const file = new File([cachedBlob], `${safeTitle}.mp4`, { type: 'video/mp4' });
  try {
    await navigator.share({ files: [file], title: title || 'Tadabbur Reminder', text: 'Reflect on this reminder.' });
    return true;
  } catch (e) {
    if (e.name === 'AbortError') return false;
    return false;
  }
}

/* ── History / Progress / Profile / Admin (preserved) ──────────────────── */
async function renderHistory(app) {
  const user = await getUser();
  if (!user) { navigate('/'); return; }
  app.innerHTML = `${navHtml('')}<div class="page"><div class="empty-state"><p>History coming soon.</p></div></div>`;
}

async function renderProgress(app) {
  const user = await getUser();
  if (!user) { navigate('/'); return; }
  try {
    const p = await API.get('/progress/weekly', 60);
    app.innerHTML = `${navHtml('')}<div class="page">
      <h1 class="page-title">Weekly Progress</h1>
      <div class="card"><p>Posted ${p.posted_count || 0} of 7 days this week.</p></div>
    </div>`;
  } catch (e) {
    app.innerHTML = `${navHtml('')}<div class="page"><div class="empty-state"><p>${escHtml(e.message)}</p></div></div>`;
  }
}

async function renderProfile(app) {
  const user = await getUser();
  if (!user) { navigate('/'); return; }
  app.innerHTML = `${navHtml('')}<div class="page">
    <h1 class="page-title">Profile</h1>
    <div class="card">
      <p><strong>Name:</strong> ${escHtml(user.display_name)}</p>
      <p><strong>Role:</strong> ${escHtml(user.role)}</p>
      <button class="btn btn-outline" data-logout>Sign Out</button>
    </div>
  </div>`;
  bindLogout();
}

async function renderAdmin(app) {
  const user = await getUser();
  if (!user || (user.role !== 'admin' && user.role !== 'curator')) { navigate('/home'); return; }
  app.innerHTML = `${navHtml('')}<div class="page">
    <h1 class="page-title">Admin</h1>
    <div class="card"><p>Admin panel coming soon.</p></div>
  </div>`;
}
