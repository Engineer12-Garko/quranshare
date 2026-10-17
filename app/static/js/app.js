/* ══════════════════════════════════════════════════════════════════════════ */
/* TADABBUR — Reflect. Understand. Remember.                                 */
/* ══════════════════════════════════════════════════════════════════════════ */

/* ── API client ──────────────────────────────────────────────────────────── */
let _apiCache = {};
// Keep only a small number of prepared files in memory; video streams can be large.
const _videoCache = new Map();
const MAX_PREPARED_VIDEO_BYTES = 100 * 1024 * 1024;
const MAX_PREPARED_CACHE_BYTES = 150 * 1024 * 1024;
const MAX_PREPARED_CACHE_FILES = 2;
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

/* ── Prepared video file cache ──────────────────────────────────────────── */
function cachePreparedVideo(videoId, file) {
  _videoCache.delete(videoId);
  let total = [..._videoCache.values()].reduce((sum, entry) => sum + entry.file.size, 0);
  while (_videoCache.size && (_videoCache.size >= MAX_PREPARED_CACHE_FILES || total + file.size > MAX_PREPARED_CACHE_BYTES)) {
    const oldestId = _videoCache.keys().next().value;
    total -= _videoCache.get(oldestId).file.size;
    _videoCache.delete(oldestId);
  }
  _videoCache.set(videoId, { file, preparedAt: Date.now() });
}

function videoShareStatus(button, message, isError = false) {
  const host = button?.closest?.('.video-actions') || button?.parentElement;
  if (!host) return;
  let status = host.querySelector('.video-share-status');
  if (!status) {
    status = document.createElement('div');
    status.className = 'video-share-status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    host.appendChild(status);
  }
  status.textContent = message;
  status.classList.toggle('is-error', isError);
}

function makeVideoFileName(title) {
  const stem = (title || 'Tadabbur Reminder')
    .normalize('NFKD').replace(/[^\w -]/g, '').trim().replace(/[\s-]+/g, '_').slice(0, 80) || 'Tadabbur_Reminder';
  return `${stem}.mp4`;
}

async function prepareVideoFile(videoId, title, button) {
  const response = await fetch(`/api/v1/videos/${encodeURIComponent(videoId)}/stream`, { credentials: 'same-origin' });
  if (response.status !== 200 || !response.ok) throw new Error(`Video download failed (HTTP ${response.status}).`);
  if (response.redirected) throw new Error('The video endpoint redirected instead of returning the video file.');
  const contentType = (response.headers.get('content-type') || '').split(';', 1)[0].trim().toLowerCase();
  if (contentType !== 'video/mp4') throw new Error('The server did not return an MP4 video. Please try again later.');
  const declaredSize = Number(response.headers.get('content-length'));
  if (Number.isFinite(declaredSize) && declaredSize > MAX_PREPARED_VIDEO_BYTES) {
    throw new Error('This video is too large to prepare for sharing on this device.');
  }

  videoShareStatus(button, 'Preparing video for sharing. Keep this page open…');
  let blob;
  if (response.body?.getReader) {
    const reader = response.body.getReader();
    const chunks = [];
    let received = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      received += value.byteLength;
      if (received > MAX_PREPARED_VIDEO_BYTES) {
        await reader.cancel();
        throw new Error('This video is too large to prepare for sharing on this device.');
      }
      chunks.push(value);
      const progress = declaredSize > 0 ? ` (${Math.min(99, Math.round(received / declaredSize * 100))}%)` : '';
      videoShareStatus(button, `Preparing video for sharing${progress}…`);
    }
    blob = new Blob(chunks, { type: 'video/mp4' });
  } else {
    blob = await response.blob();
  }
  if (blob.size < 12 || blob.size > MAX_PREPARED_VIDEO_BYTES) throw new Error('The video file is empty or exceeds the sharing size limit.');
  const header = new Uint8Array(await blob.slice(0, 12).arrayBuffer());
  if (String.fromCharCode(...header.slice(4, 8)) !== 'ftyp') throw new Error('The server response is not a valid MP4 video.');

  const file = new File([blob], makeVideoFileName(title), { type: 'video/mp4', lastModified: Date.now() });
  cachePreparedVideo(videoId, file);
  return file;
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
  const now = new Date();
  const dayOfYear = Math.floor((Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) - Date.UTC(now.getFullYear(), 0, 0)) / 86400000);
  return VERSES[dayOfYear % VERSES.length];
}

function todayDua() {
  const now = new Date();
  const dayOfYear = Math.floor((Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) - Date.UTC(now.getFullYear(), 0, 0)) / 86400000);
  return DUAS[dayOfYear % DUAS.length];
}

/* ── Saved/Bookmarks (localStorage) ────────────────────────────────────── */
function savedStorageKey() {
  return _currentUser?.id ? `tadabbur_saved_${_currentUser.id}` : null;
}

function getSaved() {
  const key = savedStorageKey();
  if (!key) return [];
  try { return JSON.parse(localStorage.getItem(key) || '[]'); } catch { return []; }
}
function setSaved(items) {
  const key = savedStorageKey();
  if (key) localStorage.setItem(key, JSON.stringify(items));
}
function isSaved(type, id) { return getSaved().some(s => s.type === type && s.id === id); }
function toggleSaved(type, id, title) {
  const saved = getSaved();
  const idx = saved.findIndex(s => s.type === type && s.id === id);
  if (idx >= 0) saved.splice(idx, 1);
  else saved.push({ type, id, title });
  setSaved(saved);
  return idx < 0;
}

function getLegacySaved() {
  try { return JSON.parse(localStorage.getItem('tadabbur_saved') || '[]'); } catch { return []; }
}

function importLegacySaved() {
  const key = savedStorageKey();
  if (!key) return;
  const importsKey = `${key}_legacy_imported`;
  if (localStorage.getItem(importsKey)) return;
  const existing = getSaved();
  const legacy = getLegacySaved();
  const merged = [...existing];
  for (const item of legacy) {
    if (!merged.some(saved => saved.type === item.type && saved.id === item.id)) merged.push(item);
  }
  setSaved(merged);
  localStorage.setItem(importsKey, '1');
  renderSaved(document.getElementById('app'));
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
        <path d="M60 20 C48 8, 32 4, 18 4 V84 C32 84, 48 88, 60 100 C72 88, 88 84, 102 84 V4 C88 4, 72 8, 60 20 Z" fill="currentColor" opacity="0.9"/>
        <path d="M60 20 V100" stroke="white" stroke-width="2"/>
        <path d="M18 4 V84 C32 84, 48 88, 60 100 V20 C48 8, 32 4, 18 4 Z" fill="currentColor" opacity="0.7"/>
        <path d="M102 4 V84 C88 84, 72 88, 60 100 V20 C72 8, 88 4, 102 4 Z" fill="currentColor" opacity="0.7"/>
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
    <div style="min-height:100dvh;display:flex;align-items:center;justify-content:center;padding:24px;">
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
async function loadVerseOfDay() {
  const now = new Date();
  const localDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  try {
    const verse = await API.get(`/content/verse-of-day?date=${encodeURIComponent(localDate)}`, 3600);
    localStorage.setItem('tadabbur_quran_verse_cache', JSON.stringify({ localDate, verse }));
    return verse;
  } catch {
    try {
      const cached = JSON.parse(localStorage.getItem('tadabbur_quran_verse_cache') || 'null');
      if (cached?.localDate === localDate && cached.verse?.arabic && cached.verse?.translation) return cached.verse;
    } catch {}
    const fallback = todayVerse();
    return {
      verse_key: fallback.ref.replace(/^Qur'an\s+/i, ''),
      arabic: fallback.arabic,
      translation: fallback.translation,
    };
  }
}

async function renderHome(app) {
  const user = await getUser();
  if (!user) { navigate('/'); return; }
  app.innerHTML = `${navHtml('#/home')}<div class="page" id="home-content"><div class="empty-state"><p>Loading...</p></div></div>`;

  try {
    const video = await API.get('/reminders/today');
    const verse = await loadVerseOfDay();
    app.querySelector('#home-content').innerHTML = `
      <div class="page-header">
        <span class="brand">TADABBUR</span>
        <button class="icon-btn material-symbols-outlined" onclick="navigate('/settings')">menu</button>
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
            <button class="watch-link watch-link-button" onclick="watchVideo(${video.id})" type="button">▶ Watch Reminder</button>
            <button class="btn btn-primary btn-sm" type="button" onclick="shareVideoFile(${video.id}, '${escHtml(video.title).replace(/'/g, "\\'")}', this)">Share video</button>
          </div>
        </div>
      </div>
      <div class="section-title">QUR'AN VERSE OF THE DAY</div>
      <div class="verse-card">
        <div class="verse-arabic" dir="rtl" lang="ar" translate="no">${escHtml(verse.arabic)}</div>
        <div class="verse-translation" translate="no">${escHtml(verse.translation)}</div>
        <div class="verse-ref">Qur'an ${escHtml(verse.verse_key)}</div>
        ${verse.source ? `<div class="verse-attribution">${escHtml(verse.source)}${verse.translation_source ? ` · Translation: ${escHtml(verse.translation_source)}` : ''}</div>` : ''}
        <a href="#/videos" class="verse-link">Read & Reflect →</a>
      </div>`;
  } catch (e) {
    app.querySelector('#home-content').innerHTML = `<div class="empty-state"><p>${escHtml(e.message)}</p></div>`;
  }
}

/* ── Videos Screen ─────────────────────────────────────────────────────── */
let _videoSearch = '';
let _videoCategory = 'All';
let _videoCategoryId = null;

async function renderVideos(app) {
  const user = await getUser();
  if (!user) { navigate('/'); return; }
  app.innerHTML = `${navHtml('#/videos')}<div class="page" id="videos-content"><div class="empty-state"><p>Loading...</p></div></div>`;

  let categories = [{ id: null, name: 'All' }];
  try {
    const loadedCategories = await API.get('/categories', 300);
    categories = categories.concat((loadedCategories || []).map(c => ({ id: c.id, name: c.name })));
  } catch (e) {
    console.error('Unable to load video categories', e);
  }

  function pillHtml() {
    return `<div class="pill-row-inner">` + categories.map((c, i) =>
      (i > 0 ? '<span class="pill-divider">|</span>' : '') +
      `<button class="pill ${_videoCategory === c.name ? 'active' : ''}" onclick='setVideoCategory(${JSON.stringify(c.name)}, ${c.id === null ? 'null' : c.id})'>${escHtml(c.name)}</button>`
    ).join('') + `</div>`;
  }

  async function loadVideos() {
    const el = app.querySelector('#videos-content');
    if (!el) return;
    try {
      const qs = new URLSearchParams({ skip: 0, limit: 100 });
      if (_videoSearch) qs.set('search', _videoSearch);
      if (_videoCategoryId !== null) qs.set('category_id', _videoCategoryId);
      const res = await API.get('/videos?' + qs.toString(), 60);
      let items = res.items || [];

      const cards = items.map(v => `
        <div class="video-card">
          <div class="video-thumb">
            <button class="play-icon material-symbols-outlined" onclick="watchVideo(${v.id})" type="button" aria-label="Watch ${escHtml(v.title)}">play_arrow</button>
          </div>
          <div class="video-info">
            <div class="video-title">${escHtml(v.title)}</div>
            ${v.description ? `<div class="video-desc">${escHtml(v.description)}</div>` : ''}
            ${v.duration_seconds ? `<div class="video-duration">Duration: ${fmtDuration(v.duration_seconds)}</div>` : ''}
            <div class="video-actions">
              <button class="watch-link watch-link-button" onclick="watchVideo(${v.id})" type="button">▶ Watch Reminder</button>
              <button class="btn btn-primary btn-sm" type="button" onclick="shareVideoFile(${v.id}, '${escHtml(v.title).replace(/'/g, "\\'")}', this)">Share video</button>
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
        <div class="pill-row">${pillHtml()}</div>
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

function setVideoCategory(cat, categoryId) {
  _videoCategory = cat;
  _videoCategoryId = categoryId === undefined ? null : categoryId;
  _videoSearch = '';
  renderVideos(document.getElementById('app'));
}

/* ── Du'as Screen ──────────────────────────────────────────────────────── */
let _duaCategory = 'All';
let _duaSearch = '';

async function renderDuas(app) {
  const user = await getUser();
  if (!user) { navigate('/'); return; }
  app.innerHTML = `${navHtml('#/duas')}<div class="page" id="duas-content"><div class="empty-state"><p>Loading...</p></div></div>`;

  const categories = ['All', 'Morning', 'Evening', 'Sleep', 'More'];

  const duaOfDay = todayDua();

  function pillHtml() {
    return `<div class="pill-row-inner">` + categories.map((c, i) =>
      (i > 0 ? '<span class="pill-divider">|</span>' : '') +
      `<button class="pill ${_duaCategory === c ? 'active' : ''}" onclick="setDuaCategory('${c}')">${c}</button>`
    ).join('') + `</div>`;
  }

  function renderList() {
    const el = app.querySelector('#duas-content');
    if (!el) return;

    const query = _duaSearch.toLocaleLowerCase();
    const filtered = DUAS.filter(d => {
      if (['Morning', 'Evening', 'Sleep'].includes(_duaCategory) && d.category !== _duaCategory) return false;
      if (_duaCategory === 'More' && ['Morning', 'Evening', 'Sleep'].includes(d.category)) return false;
      if (!query) return true;
      return [d.title, d.category, d.translation, d.transliteration]
        .filter(Boolean)
        .some(value => value.toLocaleLowerCase().includes(query));
    });
    const moreDuas = filtered.filter(d => d.id !== duaOfDay.id);

    el.innerHTML = `
      <div class="page-header">
        <span class="brand">TADABBUR</span>
      </div>
      <h1 class="page-title">Daily Du'as</h1>
      <p class="page-subtitle">Supplications For Everyday</p>
      <div class="search-wrap">
        <span class="search-icon material-symbols-outlined">search</span>
        <input id="dua-search" class="search-input" type="text" placeholder="Search du'as..." value="${escHtml(_duaSearch)}" />
      </div>
      <div class="pill-row">${pillHtml()}</div>
      <div class="section-title">DU'A OF THE DAY</div>
      <div class="dua-card">
        <div class="dua-arabic" dir="rtl" lang="ar" translate="no">${escHtml(duaOfDay.arabic)}</div>
        <div class="dua-translation">${escHtml(duaOfDay.translation)}</div>
        <div class="dua-actions">
          <button class="btn btn-primary btn-sm" type="button" onclick="openDuaDetails('${escHtml(duaOfDay.id)}')">Read Du'a →</button>
          <button class="btn btn-outline btn-sm" type="button" onclick="toggleDuaSaved('${escHtml(duaOfDay.id)}')">${isSaved('dua', duaOfDay.id) ? '🔖 Saved' : '🔖 Save'}</button>
        </div>
      </div>
      <div class="section-title">MORE DAILY DU'AS</div>
      ${moreDuas.map(d => `
        <div class="dua-list-card">
          <div class="dua-icon">${d.icon}</div>
          <div class="dua-list-info">
            <div class="dua-list-title">${escHtml(d.title)}</div>
            <div class="dua-list-sub">${escHtml(d.category)}</div>
          </div>
          <button class="dua-arrow" type="button" aria-label="Read ${escHtml(d.title)}" onclick="openDuaDetails('${escHtml(d.id)}')">→</button>
          <button class="bookmark-btn" type="button" aria-label="${isSaved('dua', d.id) ? 'Remove saved' : 'Save'} ${escHtml(d.title)}" onclick="toggleDuaSaved('${escHtml(d.id)}')">${isSaved('dua', d.id) ? '🔖' : '♡'}</button>
        </div>
      `).join('')}
      ${moreDuas.length === 0 ? '<div class="empty-state"><p>No du\'as match this search or category.</p></div>' : ''}
    `;

    const searchInput = el.querySelector('#dua-search');
    let searchTimer;
    searchInput.addEventListener('input', e => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => { _duaSearch = e.target.value.trim(); renderList(); }, 350);
    });
  }

  renderList();
}

function setDuaCategory(cat) { _duaCategory = cat; _duaSearch = ''; renderDuas(document.getElementById('app')); }

function toggleDuaSaved(duaId) {
  const dua = DUAS.find(item => item.id === duaId);
  if (!dua) return;
  toggleSaved('dua', dua.id, dua.title);
  if (window.location.hash === '#/saved') renderSaved(document.getElementById('app'));
  else renderDuas(document.getElementById('app'));
}

function openDuaDetails(duaId) {
  const dua = DUAS.find(item => item.id === duaId);
  if (!dua) return;
  document.getElementById('dua-details-modal')?.remove();
  const modal = document.createElement('div');
  modal.id = 'dua-details-modal';
  modal.className = 'dua-details-overlay';
  modal.innerHTML = `
    <section class="dua-details-dialog" role="dialog" aria-modal="true" aria-labelledby="dua-details-title">
      <button class="dua-details-close" type="button" aria-label="Close" onclick="document.getElementById('dua-details-modal').remove()">×</button>
      <div class="dua-list-sub">${escHtml(dua.category)}</div>
      <h2 id="dua-details-title" class="dua-list-title">${escHtml(dua.title)}</h2>
      <div class="dua-arabic" dir="rtl" lang="ar" translate="no">${escHtml(dua.arabic)}</div>
      <p class="dua-translation">${escHtml(dua.translation)}</p>
      ${dua.transliteration ? `<p class="dua-transliteration">${escHtml(dua.transliteration)}</p>` : ''}
      ${dua.source ? `<p class="dua-source">${escHtml(dua.source)}</p>` : '<p class="dua-source">Source details are not available for this entry.</p>'}
      <button class="btn btn-outline btn-sm" type="button" onclick="toggleDuaSaved('${escHtml(dua.id)}'); openDuaDetails('${escHtml(dua.id)}')">${isSaved('dua', dua.id) ? '🔖 Unsave' : '🔖 Save Du\'a'}</button>
    </section>`;
  document.body.appendChild(modal);
  modal.addEventListener('click', event => { if (event.target === modal) modal.remove(); });
  modal.addEventListener('keydown', event => { if (event.key === 'Escape') modal.remove(); });
}

/* ── Saved Screen ──────────────────────────────────────────────────────── */
async function renderSaved(app) {
  const user = await getUser();
  if (!user) { navigate('/'); return; }
  app.innerHTML = `${navHtml('#/saved')}<div class="page" id="saved-content"><div class="empty-state"><p>Loading...</p></div></div>`;

  const saved = getSaved();
  const videoItems = saved.filter(s => s.type === 'video');
  const duaItems = saved.filter(s => s.type === 'dua');
  const duaMap = Object.fromEntries(DUAS.map(d => [d.id, d]));
  const legacyImportAvailable = getLegacySaved().length > 0 && !localStorage.getItem(`${savedStorageKey()}_legacy_imported`);

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
          <div class="saved-actions">
            <button class="btn btn-primary btn-sm" onclick="watchVideo(${s.id})">Watch Reminder</button>
            <button class="bookmark-btn" onclick="toggleSaved('video', ${s.id}); renderSaved(document.getElementById('app'));" title="Remove">🔖</button>
          </div>
        </div>
      </div>
    `).join('');

    const duaCards = duaItems.map(s => {
      const d = duaMap[s.id] || { title: s.title, icon: '📖', category: '' };
      return `
        <div class="dua-saved-card">
          <div class="dua-list-info">
            <div class="dua-list-title">${escHtml(d.title)}</div>
            ${d.category ? `<div class="dua-list-sub">${d.category}</div>` : ''}
          </div>
          <button class="btn btn-primary btn-sm" type="button" onclick="openDuaDetails('${escHtml(s.id)}')">Read</button>
          <button class="bookmark-btn" onclick="toggleSaved('dua', '${escHtml(s.id)}'); renderSaved(document.getElementById('app'));" title="Remove">🔖</button>
        </div>
      `;
    }).join('');

    el.innerHTML = `
      <div class="page-header">
        <span class="brand">TADABBUR</span>
      </div>
      <h1 class="page-title">Your Saved Reminders</h1>
      <p class="page-subtitle">Keep the reminders that matter to you.</p>
      ${legacyImportAvailable ? `<div class="card legacy-saves-card"><p>This browser has bookmarks from before saves were separated by profile.</p><button class="btn btn-outline btn-sm" type="button" onclick="importLegacySaved()">Import these bookmarks into this profile</button></div>` : ''}
      <div class="pill-row">
        <div class="pill-row-inner">
          <button class="pill active">All</button>
          <span class="pill-divider">|</span>
          <button class="pill">Videos</button>
          <span class="pill-divider">|</span>
          <button class="pill">Du'as</button>
        </div>
      </div>
      ${videoItems.length === 0 && duaItems.length === 0 ? `
        <div class="empty-state">
          <div class="empty-icon">📖</div>
          <p>No saved reminders yet.</p>
          <p style="font-size:0.8rem;margin-top:4px;">Bookmark videos and du'as to see them here.</p>
        </div>
      ` : `
        ${videoItems.length > 0 ? `<div class="section-title">SAVED VIDEOS</div>${videoCards}` : ''}
        ${duaItems.length > 0 ? `<div class="section-title">SAVED DU'AS</div><div class="dua-saved-grid">${duaCards}</div>` : ''}
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
        <div class="gear-icon material-symbols-outlined">settings</div>
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
        <span class="settings-value">7:00 AM</span>
        <span class="settings-arrow">›</span>
      </div>
      <div class="settings-card">
        <div class="settings-icon material-symbols-outlined">self_improvement</div>
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
        <span class="settings-arrow">›</span>
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
  const existing = document.getElementById('video-modal');
  if (existing) existing.remove();

  const modal = document.createElement('div');
  modal.id = 'video-modal';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:200;display:flex;align-items:center;justify-content:center;padding:16px;';
  modal.innerHTML = `
    <div style="background:var(--color-card);border-radius:20px;max-width:480px;width:100%;overflow:hidden;position:relative;">
      <button onclick="document.getElementById('video-modal').remove()" style="position:absolute;top:12px;right:12px;z-index:10;background:rgba(0,0,0,.5);color:#fff;border:none;border-radius:50%;width:36px;height:36px;font-size:1.2rem;cursor:pointer;">✕</button>
      <video id="modal-video" controls autoplay playsinline preload="metadata" style="width:100%;max-height:70vh;background:#000;" src="/api/v1/videos/${videoId}/stream"></video>
      <div id="modal-video-info" style="padding:16px;"><div style="color:var(--color-muted);">Loading video...</div></div>
    </div>`;
  document.body.appendChild(modal);
  modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });

  const player = modal.querySelector('#modal-video');
  player.addEventListener('error', () => {
    const info = modal.querySelector('#modal-video-info');
    if (info) info.innerHTML = '<div style="color:#a33;">Unable to load this video. Please try again later.</div>';
  }, { once: true });

  API.get(`/videos/${videoId}`).then(v => {
    const info = document.getElementById('modal-video-info');
    if (info) {
      info.innerHTML = `
        <div style="font-weight:800;font-size:1.1rem;margin-bottom:4px;">${escHtml(v.title)}</div>
        ${v.description ? `<div style="font-size:.85rem;color:var(--color-muted);margin-bottom:12px;">${escHtml(v.description)}</div>` : ''}
        ${v.duration_seconds ? `<div style="font-size:.8rem;color:var(--color-muted);">Duration: ${fmtDuration(v.duration_seconds)}</div>` : ''}
        <div class="video-actions" style="margin-top:12px;"><button class="btn btn-primary btn-sm" style="width:100%;" type="button" onclick="shareVideoFile(${v.id}, '${escHtml(v.title).replace(/'/g, "\\'")}', this)">Share video</button></div>
      `;
    }
  }).catch(() => {});

}

/* ── Share ─────────────────────────────────────────────────────────────── */
async function sharePreparedVideo(videoId, title, button, file) {
  if (!navigator.share) {
    button.dataset.shareDownload = 'true';
    button.textContent = 'Download video';
    videoShareStatus(button, 'This browser cannot share video files. Tap “Download video” to save the MP4 and share it manually.');
    return false;
  }
  if (navigator.canShare && !navigator.canShare({ files: [file] })) {
    button.dataset.shareDownload = 'true';
    button.textContent = 'Download video';
    videoShareStatus(button, 'This device cannot share video files here. Tap “Download video” to save the MP4 and share it manually.');
    return false;
  }

  // Call Web Share synchronously in this click handler before the first await.
  let sharePromise;
  try {
    sharePromise = navigator.share({ files: [file] });
  } catch (error) {
    sharePromise = Promise.reject(error);
  }
  try {
    await sharePromise;
  } catch (error) {
    if (error?.name === 'AbortError') {
      videoShareStatus(button, 'Share cancelled. Your video has not been marked as posted.');
      return false;
    }
    console.error('Unable to share video file', error);
    if (error?.name === 'TypeError') {
      button.dataset.shareDownload = 'true';
      button.textContent = 'Download video';
      videoShareStatus(button, 'This browser cannot share video files here. Tap “Download video” to save the MP4 and share it manually.');
      return false;
    }
    const message = error?.name === 'NotAllowedError'
      ? 'The share action expired. Tap “Share video now” to try again.'
      : `Unable to share this video${error?.message ? `: ${error.message}` : '. Please try again.'}`;
    videoShareStatus(button, message, true);
    return false;
  }

  videoShareStatus(button, 'The share sheet finished. Complete posting in WhatsApp if you want to share to Status.');
  try {
    await API.post(`/videos/${encodeURIComponent(videoId)}/share`);
  } catch (error) {
    console.error('Video was shared but share activity could not be recorded', error);
    videoShareStatus(button, 'The share sheet finished, but Tadabbur could not save this activity. Complete posting in WhatsApp if desired.', true);
  }
  return true;
}

function downloadPreparedVideo(videoId, button) {
  const cached = _videoCache.get(videoId);
  if (!cached) {
    button.dataset.shareDownload = '';
    button.textContent = 'Share video';
    videoShareStatus(button, 'The prepared video is no longer available. Tap Share video to prepare it again.', true);
    return;
  }
  const objectUrl = URL.createObjectURL(cached.file);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = cached.file.name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
  videoShareStatus(button, 'MP4 download started. Share the downloaded video manually.');
}

async function shareVideoFile(videoId, title, button) {
  if (!button) return false;
  if (button.dataset.shareDownload === 'true') {
    downloadPreparedVideo(videoId, button);
    return false;
  }

  let cached = _videoCache.get(videoId);
  if (cached) {
    // Refresh insertion order to keep the most recently used file in cache.
    _videoCache.delete(videoId);
    _videoCache.set(videoId, cached);
    if (!navigator.share || (navigator.canShare && !navigator.canShare({ files: [cached.file] }))) {
      button.dataset.shareDownload = 'true';
      button.textContent = 'Download video';
      videoShareStatus(button, 'File sharing is unsupported here. Tap “Download video” to save the MP4 and share it manually.');
      return false;
    }
    button.textContent = 'Share video now';
    return sharePreparedVideo(videoId, title, button, cached.file);
  }

  button.disabled = true;
  button.textContent = 'Preparing video…';
  videoShareStatus(button, 'Preparing the actual MP4 video first. You will need to tap “Share video now” once it is ready.');
  try {
    const file = await prepareVideoFile(videoId, title, button);
    // Keep the final native share action on its own, fresh user tap.
    if (navigator.share && (!navigator.canShare || navigator.canShare({ files: [file] }))) {
      button.textContent = 'Share video now';
      button.dataset.shareDownload = '';
      videoShareStatus(button, 'Video ready. Tap “Share video now” to send the MP4 to the native share sheet.');
    } else {
      button.disabled = false;
      button.dataset.shareDownload = 'true';
      button.textContent = 'Download video';
      videoShareStatus(button, 'Video ready. This browser cannot share video files; tap “Download video” to save the MP4 and share it manually.');
    }
  } catch (error) {
    console.error('Unable to prepare video file', error);
    button.textContent = 'Try again';
    videoShareStatus(button, `${error?.message || 'Unable to prepare this video.'} Tap to try again.`, true);
  } finally {
    button.disabled = false;
  }
  return false;
}

/* ── History / Progress / Profile / Admin (preserved) ──────────────────── */
async function renderHistory(app) {
  const user = await getUser();
  if (!user) { navigate('/'); return; }
  app.innerHTML = `${navHtml('')}<div class="page" id="history-content"><div class="empty-state"><p>Loading...</p></div></div>`;
  try {
    const history = await API.get('/history?skip=0&limit=100');
    const rows = (history.items || []).map(item => `
      <div class="card" style="margin-bottom:12px;">
        <strong>Video #${item.video_id}</strong>
        <div style="color:var(--color-muted);font-size:.85rem;">${escHtml(item.action.replace('_', ' '))} · ${new Date(item.posted_at).toLocaleString()}</div>
      </div>`).join('');
    app.querySelector('#history-content').innerHTML = `<div class="page">
      <h1 class="page-title">History</h1>
      <p class="page-subtitle">Your recent reminder activity.</p>
      ${rows || '<div class="empty-state"><p>No activity yet.</p></div>'}
    </div>`;
  } catch (e) {
    app.querySelector('#history-content').innerHTML = `<div class="empty-state"><p>${escHtml(e.message)}</p></div>`;
  }
}

async function renderProgress(app) {
  const user = await getUser();
  if (!user) { navigate('/'); return; }
  try {
    const p = await API.get('/progress/weekly', 60);
    const days = (p.days || []).map(day =>
      `<div class="card" style="display:flex;justify-content:space-between;margin-bottom:8px;">
        <span>${escHtml(day.date)}</span><strong>${day.posted ? `${day.count} posted` : 'Not posted'}</strong>
      </div>`).join('');
    app.innerHTML = `${navHtml('')}<div class="page">
      <h1 class="page-title">Weekly Progress</h1>
      <div class="card"><p>Posted ${p.total_posted || 0} reminders this week.</p><p>${escHtml(p.week_start)} to ${escHtml(p.week_end)}</p></div>
      <div style="margin-top:16px;">${days}</div>
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
  app.innerHTML = `${navHtml('')}<div class="page" id="admin-content"><div class="empty-state"><p>Loading...</p></div></div>`;
  try {
    const syncButton = `<button id="sync-drive" class="btn btn-primary btn-sm">Sync Google Drive</button>`;
    let users = [];
    if (user.role === 'admin') users = await API.get('/admin/users?skip=0&limit=200');
    const userRows = users.map(u => `
      <div class="card" style="margin-bottom:8px;">
        <strong>${escHtml(u.display_name)}</strong> · ${escHtml(u.role)}
        <div style="color:var(--color-muted);font-size:.85rem;">${escHtml(u.email)} · ${u.is_active ? 'Active' : 'Inactive'}</div>
      </div>`).join('');
    app.querySelector('#admin-content').innerHTML = `<div class="page">
      <h1 class="page-title">Admin</h1>
      <div class="card"><p>Synchronize the video library from Google Drive.</p>${syncButton}<p id="sync-result"></p></div>
      ${user.role === 'admin' ? `<h2 class="section-title">USERS</h2>${userRows || '<div class="empty-state"><p>No users found.</p></div>'}` : ''}
    </div>`;
    app.querySelector('#sync-drive').addEventListener('click', async e => {
      e.target.disabled = true;
      try {
        const result = await API.post('/admin/sync/google-drive');
        app.querySelector('#sync-result').textContent = result.success
          ? `Added ${result.added}, updated ${result.updated}, deactivated ${result.deactivated}.`
          : (result.error || 'Sync failed.');
      } catch (err) {
        app.querySelector('#sync-result').textContent = err.message;
      } finally {
        e.target.disabled = false;
      }
    });
  } catch (e) {
    app.querySelector('#admin-content').innerHTML = `<div class="empty-state"><p>${escHtml(e.message)}</p></div>`;
  }
}
