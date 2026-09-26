/* ── API client ──────────────────────────────────────────────────────────── */
const API = {
  async request(method, path, body = null) {
    const opts = {
      method,
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`/api/v1${path}`, opts);
    const ct = res.headers.get('content-type') || '';
    const data = ct.includes('application/json') ? await res.json() : null;
    if (!res.ok) {
      let msg = data?.detail || data?.error?.message;
      if (!msg) {
        msg = res.status >= 500 
          ? 'An unexpected server error occurred. Please try again later.' 
          : `Error (HTTP ${res.status})`;
      }
      throw Object.assign(new Error(msg), { status: res.status, data });
    }
    return data;
  },
  get:    (p)    => API.request('GET',    p),
  post:   (p, b) => API.request('POST',   p, b),
  patch:  (p, b) => API.request('PATCH',  p, b),
  delete: (p)    => API.request('DELETE', p),
};

/* ── Router (hash-based SPA) ─────────────────────────────────────────────── */
const ROUTES = {
  '/':          renderLanding,
  '/login':     renderLogin,
  '/register':  renderRegister,
  '/dashboard': renderDashboard,
  '/library':   renderLibrary,
  '/history':   renderHistory,
  '/progress':  renderProgress,
  '/profile':   renderProfile,
  '/admin':     renderAdmin,
};

let _currentUser = null;

async function getUser() {
  if (_currentUser) return _currentUser;
  try { _currentUser = await API.get('/auth/me'); return _currentUser; }
  catch { return null; }
}

function clearUser() { _currentUser = null; }

function navigate(path) {
  window.location.hash = path;
}

async function route() {
  const hash = window.location.hash.slice(1) || '/';
  const handler = ROUTES[hash] || renderLanding;
  const app = document.getElementById('app');
  app.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
  try { await handler(app); }
  catch (e) {
    console.error(e);
    app.innerHTML = `<div class="auth-page"><div class="auth-card"><p class="alert alert-error">${escHtml(e.message)}</p><a href="#/dashboard">← Back</a></div></div>`;
  }
}

window.addEventListener('hashchange', route);
window.addEventListener('DOMContentLoaded', route);

/* ── Helpers ─────────────────────────────────────────────────────────────── */
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

function fmtTime(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

function fmtDuration(secs) {
  if (!secs) return '';
  const m = Math.floor(secs / 60), s = secs % 60;
  return `${m}:${String(s).padStart(2,'0')}`;
}

function dayName(isoDate) {
  return new Date(isoDate + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'short' });
}

function showAlert(container, msg, type = 'error') {
  const el = container.querySelector('.alert') || document.createElement('div');
  el.className = `alert alert-${type}`;
  el.textContent = msg;
  if (!el.parentElement) container.prepend(el);
}

function clearAlert(container) {
  container.querySelector('.alert')?.remove();
}

/* ── Nav HTML ────────────────────────────────────────────────────────────── */
function navHtml(active, user) {
  const links = [
    { href: '#/dashboard', icon: '🏠', label: 'Home'     },
    { href: '#/library',   icon: '📚', label: 'Library'  },
    { href: '#/progress',  icon: '📊', label: 'Progress' },
    { href: '#/history',   icon: '📋', label: 'History'  },
    { href: '#/profile',   icon: '👤', label: 'Profile'  },
  ];
  if (user?.role === 'admin' || user?.role === 'curator') {
    links.push({ href: '#/admin', icon: '⚙️', label: 'Admin' });
  }
  const li = links.map(l => `
    <a href="${l.href}" class="${active === l.href ? 'active' : ''}">
      <span class="nav-icon">${l.icon}</span>${l.label}
    </a>`).join('');
  return `
    <nav class="sidebar">
      <div class="sidebar-logo">Quran<span>Flow</span></div>
      <div class="sidebar-nav">${li}</div>
      <div class="sidebar-footer">
        <button class="btn btn-secondary btn-sm btn-full" id="logout-btn">Sign out</button>
      </div>
    </nav>
    <nav class="bottom-nav"><div class="bottom-nav-inner">${li}</div></nav>`;
}

function bindLogout(el) {
  el.querySelector('#logout-btn')?.addEventListener('click', async () => {
    try { await API.post('/auth/logout'); } catch {}
    clearUser();
    navigate('/');
  });
}

function shell(active, user, innerHtml) {
  return `
    <div class="app-shell">
      ${navHtml(active, user)}
      <main class="main-content">${innerHtml}</main>
    </div>`;
}

/* ══════════════════════════════════════════════════════════════════════════ */
/* LANDING                                                                    */
/* ══════════════════════════════════════════════════════════════════════════ */
async function renderLanding(app) {
  const user = await getUser();
  if (user) { navigate('/dashboard'); return; }
  app.innerHTML = `
    <div class="landing">
      <div class="landing-hero">
        <div>
          <h1>Quran<span>Flow</span></h1>
          <p>Discover, watch, and share short Islamic reminder videos — and track your daily posting habit.</p>
          <div class="landing-cta">
            <a href="#/register" class="btn btn-primary">Get Started</a>
            <a href="#/login"    class="btn btn-secondary">Sign In</a>
          </div>
        </div>
      </div>
      <div class="landing-features">
        <div class="feature-card card">
          <div class="feature-icon">🎬</div>
          <h3>Curated Library</h3>
          <p>Short Quranic reminders organized by topic — Quran, Dua, Salah, and more.</p>
        </div>
        <div class="feature-card card">
          <div class="feature-icon">📱</div>
          <h3>WhatsApp Sharing</h3>
          <p>One tap to share your daily reminder as a WhatsApp Status.</p>
        </div>
        <div class="feature-card card">
          <div class="feature-icon">📊</div>
          <h3>Weekly Progress</h3>
          <p>Track how consistently you share reminders every week.</p>
        </div>
        <div class="feature-card card">
          <div class="feature-icon">⭐</div>
          <h3>Daily Reminder</h3>
          <p>A fresh reminder each day — avoiding ones you've recently posted.</p>
        </div>
      </div>
    </div>`;
}

/* ══════════════════════════════════════════════════════════════════════════ */
/* LOGIN                                                                      */
/* ══════════════════════════════════════════════════════════════════════════ */
async function renderLogin(app) {
  const user = await getUser();
  if (user) { navigate('/dashboard'); return; }
  app.innerHTML = `
    <div class="auth-page">
      <div class="auth-card">
        <div class="auth-logo">Quran<span>Flow</span></div>
        <div class="auth-subtitle">Sign in to your account</div>
        <form id="login-form">
          <div class="form-group">
            <label for="email">Email</label>
            <input id="email" type="email" required autocomplete="email" placeholder="you@example.com" />
          </div>
          <div class="form-group">
            <label for="password">Password</label>
            <input id="password" type="password" required autocomplete="current-password" placeholder="••••••••" />
          </div>
          <button type="submit" class="btn btn-primary btn-full">Sign In</button>
        </form>
        <p class="auth-switch">No account? <a href="#/register">Register</a></p>
      </div>
    </div>`;

  app.querySelector('#login-form').addEventListener('submit', async e => {
    e.preventDefault();
    const btn = e.target.querySelector('button[type=submit]');
    btn.disabled = true; btn.textContent = 'Signing in…';
    clearAlert(app.querySelector('.auth-card'));
    try {
      await API.post('/auth/login', {
        email:    app.querySelector('#email').value,
        password: app.querySelector('#password').value,
      });
      clearUser();
      navigate('/dashboard');
    } catch (err) {
      showAlert(app.querySelector('.auth-card'), err.message);
      btn.disabled = false; btn.textContent = 'Sign In';
    }
  });
}

/* ══════════════════════════════════════════════════════════════════════════ */
/* REGISTER                                                                   */
/* ══════════════════════════════════════════════════════════════════════════ */
async function renderRegister(app) {
  const user = await getUser();
  if (user) { navigate('/dashboard'); return; }
  app.innerHTML = `
    <div class="auth-page">
      <div class="auth-card">
        <div class="auth-logo">Quran<span>Flow</span></div>
        <div class="auth-subtitle">Create your account</div>
        <form id="reg-form">
          <div class="form-group">
            <label for="name">Display Name</label>
            <input id="name" type="text" required placeholder="Your name" maxlength="100" />
          </div>
          <div class="form-group">
            <label for="email">Email</label>
            <input id="email" type="email" required autocomplete="email" placeholder="you@example.com" />
          </div>
          <div class="form-group">
            <label for="password">Password</label>
            <input id="password" type="password" required autocomplete="new-password" placeholder="At least 8 chars, 1 uppercase, 1 digit" />
            <div class="form-hint">Min 8 characters, must include an uppercase letter and a digit.</div>
          </div>
          <div class="form-group">
            <label for="whatsapp">WhatsApp Number <span style="font-weight:400">(optional)</span></label>
            <input id="whatsapp" type="tel" placeholder="+1234567890" />
          </div>
          <button type="submit" class="btn btn-primary btn-full">Create Account</button>
        </form>
        <p class="auth-switch">Already have an account? <a href="#/login">Sign in</a></p>
      </div>
    </div>`;

  app.querySelector('#reg-form').addEventListener('submit', async e => {
    e.preventDefault();
    const btn = e.target.querySelector('button[type=submit]');
    btn.disabled = true; btn.textContent = 'Creating account…';
    clearAlert(app.querySelector('.auth-card'));
    const wa = app.querySelector('#whatsapp').value.trim();
    try {
      await API.post('/auth/register', {
        display_name:     app.querySelector('#name').value.trim(),
        email:            app.querySelector('#email').value.trim(),
        password:         app.querySelector('#password').value,
        ...(wa ? { whatsapp_number: wa } : {}),
      });
      clearUser();
      navigate('/dashboard');
    } catch (err) {
      showAlert(app.querySelector('.auth-card'), err.message);
      btn.disabled = false; btn.textContent = 'Create Account';
    }
  });
}

/* ══════════════════════════════════════════════════════════════════════════ */
/* DASHBOARD                                                                  */
/* ══════════════════════════════════════════════════════════════════════════ */
async function renderDashboard(app) {
  const user = await getUser();
  if (!user) { navigate('/login'); return; }

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  app.innerHTML = shell('#/dashboard', user, `
    <div class="greeting">${greeting}, ${escHtml(user.display_name)} 👋</div>
    <div class="greeting-sub">Here is today's reminder for you.</div>

    <div id="reminder-area"><div class="loading-overlay"><div class="spinner"></div></div></div>

    <div class="mt-24">
      <div class="section-title">This Week</div>
      <div id="progress-area"><div class="loading-overlay"><div class="spinner"></div></div></div>
    </div>
  `);
  bindLogout(app);

  // Load reminder and progress in parallel
  const [reminderResult, progressResult] = await Promise.allSettled([
    API.get('/reminders/today'),
    API.get('/progress/weekly'),
  ]);

  // Render reminder
  const ra = app.querySelector('#reminder-area');
  if (reminderResult.status === 'fulfilled') {
    const v = reminderResult.value;
    ra.innerHTML = `
      <div class="card">
        <div class="reminder-wrap">
          <div>
            <div class="video-player-wrap">
              <video id="dash-video" controls preload="metadata"
                src="/api/v1/videos/${v.id}/stream"
                poster="">
                Your browser does not support video playback.
              </video>
            </div>
          </div>
          <div class="reminder-actions">
            <div>
              <div class="video-title">${escHtml(v.title)}</div>
              <div class="video-meta">
                ${v.category_name ? `<span>📁 ${escHtml(v.category_name)}</span>` : ''}
                ${v.duration_seconds ? `<span>⏱ ${fmtDuration(v.duration_seconds)}</span>` : ''}
              </div>
            </div>
            <button class="whatsapp-btn" id="share-btn" data-id="${v.id}">
              <span>📤</span> Share to WhatsApp
            </button>
            <button class="btn btn-primary mark-posted-btn" id="posted-btn" data-id="${v.id}" disabled>
              ✅ Mark as Posted
            </button>
            <p class="text-muted" id="posted-hint">Share the video first, then mark it as posted.</p>
            <a href="#/library" class="btn btn-secondary btn-sm">Browse Library</a>
          </div>
        </div>
      </div>`;

    bindShareAndPost(app, v.id, v.title);
  } else {
    const status = reminderResult.reason?.status;
    if (status === 404) {
      ra.innerHTML = `<div class="card empty-state"><div class="empty-icon">📭</div><p>No videos in the library yet. Check back soon!</p></div>`;
    } else {
      ra.innerHTML = `<div class="alert alert-error">Could not load today's reminder: ${escHtml(reminderResult.reason?.message || 'Unknown error')}</div>`;
    }
  }

  // Render weekly progress
  const pa = app.querySelector('#progress-area');
  if (progressResult.status === 'fulfilled') {
    pa.innerHTML = renderProgressWidget(progressResult.value);
  } else {
    pa.innerHTML = `<p class="text-muted">Progress unavailable.</p>`;
  }
}

/* ── Core share helper (used by dashboard, library modal, library cards) ─── */
/**
 * shareVideoFile(videoId, title)
 *
 * Priority order:
 *  1. Web Share API with File object  — lets Android/iOS pass the real MP4
 *     to WhatsApp, Telegram, etc. for Status upload.
 *  2. Web Share API with URL only     — fallback for browsers that support
 *     navigator.share but not files (e.g. desktop Chrome).
 *  3. Download the file + open wa.me  — final fallback: saves the video to
 *     the device so the user can attach it manually in WhatsApp.
 *
 * Returns true if the share sheet opened, false on hard failure.
 */
async function shareVideoFile(videoId, title, statusEl) {
  const streamUrl = `/api/v1/videos/${videoId}/stream`;

  function setStatus(msg) { if (statusEl) statusEl.textContent = msg; }

  // ── Attempt 1: Web Share with actual File ──────────────────────────────────
  if (navigator.canShare) {
    setStatus('Downloading video for sharing…');
    try {
      const resp = await fetch(streamUrl, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`Fetch failed: ${resp.status}`);
      const blob  = await resp.blob();
      const file  = new File([blob], `${title || 'reminder'}.mp4`, { type: 'video/mp4' });

      if (navigator.canShare({ files: [file] })) {
        await navigator.share({
          title:  'Islamic Reminder 🕌',
          text:   title || 'Daily Islamic Reminder',
          files:  [file],
        });
        setStatus('Shared! Now mark it as posted.');
        return true;
      }
    } catch (e) {
      // User cancelled or share failed — fall through
      if (e.name === 'AbortError') { setStatus('Share cancelled.'); return false; }
    }
  }

  // ── Attempt 2: Web Share URL only ─────────────────────────────────────────
  if (navigator.share) {
    try {
      await navigator.share({
        title: 'Islamic Reminder 🕌',
        text:  title || 'Daily Islamic Reminder',
        url:   window.location.origin + streamUrl,
      });
      setStatus('Shared! Now mark it as posted.');
      return true;
    } catch (e) {
      if (e.name === 'AbortError') { setStatus('Share cancelled.'); return false; }
    }
  }

  // ── Attempt 3: Download + wa.me ────────────────────────────────────────────
  setStatus('Downloading video… open WhatsApp and attach it as a Status.');
  try {
    // Trigger a browser download
    const a = document.createElement('a');
    a.href = streamUrl;
    a.download = `${title || 'reminder'}.mp4`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch {}
  // Open WhatsApp Status deep-link (text message with reminder caption)
  const caption = encodeURIComponent(`${title || 'Islamic Reminder'} 🕌`);
  setTimeout(() => window.open(`https://wa.me/?text=${caption}`, '_blank'), 800);
  return true;
}

function bindShareAndPost(app, videoId, videoTitle) {
  const shareBtn  = app.querySelector('#share-btn');
  const postedBtn = app.querySelector('#posted-btn');
  const hint      = app.querySelector('#posted-hint');

  shareBtn?.addEventListener('click', async () => {
    shareBtn.disabled = true;
    shareBtn.textContent = '⏳ Preparing…';
    try { await API.post(`/videos/${videoId}/share`); } catch {}

    const shared = await shareVideoFile(videoId, videoTitle, hint);

    if (shared) {
      postedBtn.disabled = false;
      shareBtn.textContent = '✅ Shared!';
      if (hint && hint.textContent === hint.textContent) // only if not already set by shareVideoFile
        hint.textContent = 'Now tap "Mark as Posted" to record it in your history.';
    } else {
      shareBtn.disabled = false;
      shareBtn.innerHTML = '<span>📤</span> Share to WhatsApp';
    }
  });

  postedBtn?.addEventListener('click', async () => {
    postedBtn.disabled = true; postedBtn.textContent = 'Saving…';
    try {
      await API.post(`/videos/${videoId}/posted`);
      postedBtn.textContent = '🎉 Posted!';
      postedBtn.classList.add('btn-secondary');
      if (hint) { hint.textContent = 'Great job! Your history and progress have been updated.'; hint.style.color = 'var(--success)'; }
      // Refresh progress widget
      try {
        const p = await API.get('/progress/weekly');
        const pa = app.querySelector('#progress-area');
        if (pa) pa.innerHTML = renderProgressWidget(p);
      } catch {}
    } catch (err) {
      postedBtn.disabled = false; postedBtn.textContent = '✅ Mark as Posted';
      showAlert(app.querySelector('.card'), err.message);
    }
  });
}

/* ══════════════════════════════════════════════════════════════════════════ */
/* LIBRARY                                                                    */
/* ══════════════════════════════════════════════════════════════════════════ */
async function renderLibrary(app) {
  const user = await getUser();
  if (!user) { navigate('/login'); return; }

  app.innerHTML = shell('#/library', user, `
    <div class="page-title">📚 Video Library</div>
    <div class="search-bar">
      <input id="search-input" type="search" placeholder="Search videos…" />
      <select id="cat-filter"><option value="">All Categories</option></select>
    </div>
    <div id="videos-area"><div class="loading-overlay"><div class="spinner"></div></div></div>
    <div id="pagination-area"></div>
  `);
  bindLogout(app);

  const catSelect = app.querySelector('#cat-filter');
  let skip = 0, limit = 12, query = '', categoryId = '';

  // Load categories
  try {
    const cats = await API.get('/categories');
    cats.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id; opt.textContent = c.name;
      catSelect.appendChild(opt);
    });
  } catch {}

  async function loadVideos() {
    const area = app.querySelector('#videos-area');
    area.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
    try {
      const params = new URLSearchParams({ skip, limit });
      if (query)      params.set('search', query);
      if (categoryId) params.set('category_id', categoryId);
      const data = await API.get(`/videos?${params}`);
      if (data.items.length === 0) {
        area.innerHTML = `<div class="empty-state"><div class="empty-icon">🔍</div><p>No videos found.</p></div>`;
      } else {
        area.innerHTML = `<div class="video-grid">${data.items.map(videoCard).join('')}</div>`;
        bindVideoCards(app);
      }
      renderPagination(app.querySelector('#pagination-area'), data.total, skip, limit, (s) => { skip = s; loadVideos(); });
    } catch (err) {
      area.innerHTML = `<div class="alert alert-error">${escHtml(err.message)}</div>`;
    }
  }

  let searchTimer;
  app.querySelector('#search-input').addEventListener('input', e => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { query = e.target.value.trim(); skip = 0; loadVideos(); }, 350);
  });
  catSelect.addEventListener('change', e => { categoryId = e.target.value; skip = 0; loadVideos(); });

  loadVideos();
}

function videoCard(v) {
  return `
    <div class="video-card" data-id="${v.id}">
      <div class="video-card-body">
        <div class="video-title">${escHtml(v.title)}</div>
        <div class="video-meta">
          ${v.category_name ? `<span>📁 ${escHtml(v.category_name)}</span>` : ''}
          ${v.duration_seconds ? `<span>⏱ ${fmtDuration(v.duration_seconds)}</span>` : ''}
        </div>
        <div class="video-actions">
          <button class="btn btn-primary btn-sm watch-btn" data-id="${v.id}">▶ Watch</button>
          <button class="btn btn-secondary btn-sm share-lib-btn" data-id="${v.id}">📤 Share</button>
        </div>
      </div>
    </div>`;
}

function bindVideoCards(container) {
  container.querySelectorAll('.watch-btn').forEach(btn => {
    btn.addEventListener('click', () => openVideoModal(btn.dataset.id));
  });
  container.querySelectorAll('.share-lib-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id    = btn.dataset.id;
      const title = btn.closest('.video-card')?.querySelector('.video-title')?.textContent || '';
      btn.disabled = true; btn.textContent = '⏳';
      try { await API.post(`/videos/${id}/share`); } catch {}
      await shareVideoFile(id, title, null);
      btn.disabled = false; btn.textContent = '📤 Share';
    });
  });
}

async function openVideoModal(videoId) {
  const existing = document.getElementById('video-modal');
  if (existing) existing.remove();

  let v;
  try { v = await API.get(`/videos/${videoId}`); }
  catch { return; }

  const modal = document.createElement('div');
  modal.id = 'video-modal';
  modal.style.cssText = `position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:100;display:flex;align-items:center;justify-content:center;padding:16px`;
  modal.innerHTML = `
    <div style="background:var(--bg);border-radius:var(--radius);max-width:480px;width:100%;padding:20px;position:relative">
      <button id="modal-close" class="btn-icon" style="position:absolute;top:12px;right:12px">✕</button>
      <div class="video-title mb-16">${escHtml(v.title)}</div>
      <div class="video-player-wrap" style="max-height:320px">
        <video controls preload="metadata" src="/api/v1/videos/${v.id}/stream" style="width:100%;height:100%;object-fit:contain"></video>
      </div>
      <div class="video-meta mt-8">
        ${v.category_name ? `<span>📁 ${escHtml(v.category_name)}</span>` : ''}
        ${v.duration_seconds ? `<span>⏱ ${fmtDuration(v.duration_seconds)}</span>` : ''}
      </div>
      ${v.description ? `<p style="font-size:.85rem;color:var(--muted);margin-top:8px">${escHtml(v.description)}</p>` : ''}
      <div class="video-actions mt-16">
        <button class="whatsapp-btn" id="modal-share" data-id="${v.id}" style="flex:1">📤 Share</button>
        <button class="btn btn-primary" id="modal-posted" data-id="${v.id}" disabled style="flex:1">✅ Mark Posted</button>
      </div>
      <p id="modal-hint" class="text-muted mt-8" style="font-size:.78rem">Share first, then mark as posted.</p>
    </div>`;
  document.body.appendChild(modal);
  modal.querySelector('#modal-close').addEventListener('click', () => modal.remove());
  modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });

  const shareBtn  = modal.querySelector('#modal-share');
  const postedBtn = modal.querySelector('#modal-posted');
  const hint      = modal.querySelector('#modal-hint');

  shareBtn.addEventListener('click', async () => {
    shareBtn.disabled = true;
    shareBtn.textContent = '⏳ Preparing…';
    try { await API.post(`/videos/${v.id}/share`); } catch {}
    const shared = await shareVideoFile(v.id, v.title, hint);
    if (shared) {
      postedBtn.disabled = false;
      shareBtn.textContent = '✅ Shared!';
    } else {
      shareBtn.disabled = false;
      shareBtn.textContent = '📤 Share';
    }
  });

  postedBtn.addEventListener('click', async () => {
    postedBtn.disabled = true; postedBtn.textContent = 'Saving…';
    try {
      await API.post(`/videos/${v.id}/posted`);
      postedBtn.textContent = '🎉 Posted!';
      hint.textContent = 'Saved to your history!'; hint.style.color = 'var(--success)';
    } catch (err) {
      hint.textContent = err.message; hint.style.color = 'var(--danger)';
      postedBtn.disabled = false; postedBtn.textContent = '✅ Mark Posted';
    }
  });
}

function renderPagination(container, total, skip, limit, cb) {
  container.innerHTML = '';
  if (total <= limit) return;
  const pages = Math.ceil(total / limit);
  const cur   = Math.floor(skip / limit);
  const el = document.createElement('div');
  el.className = 'pagination';
  if (cur > 0) {
    const b = document.createElement('button');
    b.className = 'btn btn-secondary btn-sm'; b.textContent = '← Prev';
    b.addEventListener('click', () => cb((cur - 1) * limit));
    el.appendChild(b);
  }
  const span = document.createElement('span');
  span.textContent = `Page ${cur + 1} of ${pages}`;
  el.appendChild(span);
  if (cur < pages - 1) {
    const b = document.createElement('button');
    b.className = 'btn btn-secondary btn-sm'; b.textContent = 'Next →';
    b.addEventListener('click', () => cb((cur + 1) * limit));
    el.appendChild(b);
  }
  container.appendChild(el);
}

/* ══════════════════════════════════════════════════════════════════════════ */
/* PROGRESS                                                                   */
/* ══════════════════════════════════════════════════════════════════════════ */
async function renderProgress(app) {
  const user = await getUser();
  if (!user) { navigate('/login'); return; }

  app.innerHTML = shell('#/progress', user, `
    <div class="page-title">📊 Weekly Progress</div>
    <div id="prog-area"><div class="loading-overlay"><div class="spinner"></div></div></div>
  `);
  bindLogout(app);

  try {
    const p = await API.get('/progress/weekly');
    app.querySelector('#prog-area').innerHTML = `
      <div class="card">
        ${renderProgressWidget(p)}
        <p class="text-muted mt-16">
          Keep sharing daily reminders to build your streak. Only videos you <strong>Mark as Posted</strong> count.
        </p>
      </div>`;
  } catch (err) {
    app.querySelector('#prog-area').innerHTML = `<div class="alert alert-error">${escHtml(err.message)}</div>`;
  }
}

function renderProgressWidget(p) {
  const pct = Math.round((p.total_posted / p.goal) * 100);
  const today = new Date().toISOString().slice(0, 10);
  const days = p.days.map(d => {
    const isToday = d.date === today;
    return `<div class="day-chip ${d.posted ? 'posted' : ''} ${isToday && !d.posted ? 'today' : ''}" title="${d.date}">${dayName(d.date)}</div>`;
  }).join('');
  return `
    <div class="section-title">This week — ${p.total_posted} / ${p.goal} days</div>
    <div class="progress-bar-wrap"><div class="progress-bar" style="width:${Math.min(pct,100)}%"></div></div>
    <div class="progress-days">${days}</div>`;
}

/* ══════════════════════════════════════════════════════════════════════════ */
/* HISTORY                                                                    */
/* ══════════════════════════════════════════════════════════════════════════ */
async function renderHistory(app) {
  const user = await getUser();
  if (!user) { navigate('/login'); return; }

  app.innerHTML = shell('#/history', user, `
    <div class="page-title">📋 Posting History</div>
    <div id="hist-area"><div class="loading-overlay"><div class="spinner"></div></div></div>
    <div id="hist-pag"></div>
  `);
  bindLogout(app);

  let skip = 0; const limit = 20;

  async function loadHistory() {
    const area = app.querySelector('#hist-area');
    area.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
    try {
      const data = await API.get(`/history?skip=${skip}&limit=${limit}`);
      if (data.items.length === 0) {
        area.innerHTML = `<div class="empty-state"><div class="empty-icon">📭</div><p>No posting history yet.<br>Share a reminder to get started!</p></div>`;
      } else {
        area.innerHTML = data.items.map(item => `
          <div class="history-item">
            <div class="history-thumb">🎬</div>
            <div class="history-info">
              <div class="history-title">${escHtml(item.video_title || 'Video')}</div>
              <div class="history-date">${fmtDate(item.posted_at)} ${fmtTime(item.posted_at)}</div>
            </div>
            <span class="badge ${item.action === 'posted' ? 'badge-posted' : 'badge-shared'}">
              ${item.action === 'posted' ? 'Posted' : 'Shared'}
            </span>
          </div>`).join('');
      }
      renderPagination(app.querySelector('#hist-pag'), data.total, skip, limit, s => { skip = s; loadHistory(); });
    } catch (err) {
      area.innerHTML = `<div class="alert alert-error">${escHtml(err.message)}</div>`;
    }
  }
  loadHistory();
}

/* ══════════════════════════════════════════════════════════════════════════ */
/* PROFILE                                                                    */
/* ══════════════════════════════════════════════════════════════════════════ */
async function renderProfile(app) {
  const user = await getUser();
  if (!user) { navigate('/login'); return; }
  const initial = user.display_name?.[0]?.toUpperCase() || '?';

  app.innerHTML = shell('#/profile', user, `
    <div class="page-title">👤 Profile</div>
    <div class="card">
      <div class="profile-header">
        <div class="profile-avatar">${escHtml(initial)}</div>
        <div>
          <div style="font-weight:700;font-size:1.05rem">${escHtml(user.display_name)}</div>
          <div class="text-muted">${escHtml(user.email)}</div>
          <span class="role-badge role-${user.role}">${user.role}</span>
        </div>
      </div>
      <form id="profile-form">
        <div class="form-group">
          <label for="p-name">Display Name</label>
          <input id="p-name" type="text" value="${escHtml(user.display_name)}" maxlength="100" required />
        </div>
        <div class="form-group">
          <label for="p-wa">WhatsApp Number</label>
          <input id="p-wa" type="tel" value="${escHtml(user.whatsapp_number || '')}" placeholder="+1234567890" />
          <div class="form-hint">Used for future reminder notifications. Not required for V1 sharing.</div>
        </div>
        <button type="submit" class="btn btn-primary">Save Changes</button>
      </form>
      <div id="profile-msg" class="mt-8"></div>
    </div>
    <div class="card mt-16">
      <div class="section-title">Account</div>
      <p class="text-muted mb-16">Email: ${escHtml(user.email)}</p>
      <button class="btn btn-secondary" id="profile-logout">Sign Out</button>
    </div>
  `);
  bindLogout(app);

  app.querySelector('#profile-logout').addEventListener('click', async () => {
    try { await API.post('/auth/logout'); } catch {}
    clearUser(); navigate('/');
  });

  app.querySelector('#profile-form').addEventListener('submit', async e => {
    e.preventDefault();
    const btn = e.target.querySelector('button[type=submit]');
    btn.disabled = true; btn.textContent = 'Saving…';
    const msg = app.querySelector('#profile-msg');
    msg.innerHTML = '';
    const wa = app.querySelector('#p-wa').value.trim();
    try {
      const updated = await API.patch('/users/me', {
        display_name:     app.querySelector('#p-name').value.trim(),
        ...(wa ? { whatsapp_number: wa } : { whatsapp_number: null }),
      });
      _currentUser = updated;
      msg.innerHTML = `<div class="alert alert-success">Profile updated!</div>`;
    } catch (err) {
      msg.innerHTML = `<div class="alert alert-error">${escHtml(err.message)}</div>`;
    }
    btn.disabled = false; btn.textContent = 'Save Changes';
  });
}

/* ══════════════════════════════════════════════════════════════════════════ */
/* ADMIN                                                                      */
/* ══════════════════════════════════════════════════════════════════════════ */
async function renderAdmin(app) {
  const user = await getUser();
  if (!user) { navigate('/login'); return; }
  if (user.role !== 'admin' && user.role !== 'curator') { navigate('/dashboard'); return; }

  app.innerHTML = shell('#/admin', user, `
    <div class="page-title">⚙️ Admin</div>

    <div class="card mb-16">
      <div class="section-title">Google Drive Sync</div>
      <p class="text-muted mb-16">Synchronize video metadata from Google Drive into the database.</p>
      <button class="btn btn-primary" id="sync-btn">🔄 Run Sync</button>
      <div id="sync-result" class="mt-16"></div>
    </div>

    ${user.role === 'admin' ? `
    <div class="card">
      <div class="section-title">Users</div>
      <div id="users-area"><div class="loading-overlay"><div class="spinner"></div></div></div>
    </div>` : ''}
  `);
  bindLogout(app);

  app.querySelector('#sync-btn').addEventListener('click', async () => {
    const btn = app.querySelector('#sync-btn');
    const res = app.querySelector('#sync-result');
    btn.disabled = true; btn.textContent = 'Running…';
    res.innerHTML = '';
    try {
      const data = await API.post('/admin/sync/google-drive');
      res.innerHTML = `
        <div class="sync-result card">
          <div class="stat"><span>Added</span>     <strong>${data.added}</strong></div>
          <div class="stat"><span>Updated</span>   <strong>${data.updated}</strong></div>
          <div class="stat"><span>Deactivated</span><strong>${data.deactivated}</strong></div>
          <div class="stat"><span>Failed</span>    <strong>${data.failed}</strong></div>
          <div class="stat"><span>Status</span>    <strong>${data.success ? '✅ OK' : '⚠️ Partial'}</strong></div>
        </div>`;
    } catch (err) {
      res.innerHTML = `<div class="alert alert-error">${escHtml(err.message)}</div>`;
    }
    btn.disabled = false; btn.textContent = '🔄 Run Sync';
  });

  if (user.role === 'admin') {
    try {
      const users = await API.get('/admin/users');
      const tbody = users.map(u => `
        <tr>
          <td>${escHtml(u.display_name)}</td>
          <td>${escHtml(u.email)}</td>
          <td><span class="role-badge role-${u.role}">${u.role}</span></td>
          <td>${u.is_active ? '✅' : '❌'}</td>
          <td class="text-muted">${fmtDate(u.created_at)}</td>
        </tr>`).join('');
      app.querySelector('#users-area').innerHTML = `
        <table class="users-table">
          <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Active</th><th>Joined</th></tr></thead>
          <tbody>${tbody}</tbody>
        </table>`;
    } catch (err) {
      app.querySelector('#users-area').innerHTML = `<div class="alert alert-error">${escHtml(err.message)}</div>`;
    }
  }
}
