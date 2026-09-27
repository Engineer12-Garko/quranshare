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
      if (Array.isArray(msg)) {
        msg = msg.map(e => e.msg || JSON.stringify(e)).join(', ');
      } else if (msg && typeof msg === 'object') {
        msg = JSON.stringify(msg);
      }
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

function headerHtml(active, user) {
  if (active === '#/dashboard') {
    return `
      <header class="fixed top-0 inset-x-0 z-50 bg-surface/85 backdrop-blur-xl pt-safe shadow-[0_1px_12px_rgba(14,59,46,0.04)]">
        <div class="h-16 px-space-md flex items-center justify-between gap-space-sm">
          <div class="flex items-center gap-space-sm min-w-0">
            <button aria-label="Go back" class="w-11 h-11 -ml-1.5 flex items-center justify-center rounded-full text-on-surface-variant hover:text-primary hover:bg-surface-container transition-colors shrink-0" onclick="history.back()">
              <span class="material-symbols-outlined text-[24px]">arrow_back</span>
            </button>
            <img alt="QuranFlow Emblem Logo" class="h-7 w-auto object-contain shrink-0" src="https://lh3.googleusercontent.com/aida/AEtjO1UXcSMXmwXzqpHYydkhzU82UaqJNJtpyjLr5NmX6AA0XxAb2mPnEAouljylR41cqIhCtQVOTrgastVoW0LR-3muqnz87iZrQDsyt9yQwAhU0Yy7ydA5FS59sRhoyUVV6iCYRapB67jSC8rpSJy_JuFwwDZU1rmQztuY1x_4n5QyK7oNfSZuJRlrc7D4YnBDlLpnhGmEpo3hRWkUcnsPXzG4wKfqCu8SwMjRSzwe0XK1Sxl0Vp87WOMDmIUG"/>
            <h1 class="font-headline-sm text-headline-sm text-primary tracking-tight truncate">Reflection Player</h1>
          </div>
          <div class="flex items-center gap-space-sm shrink-0">
            <button aria-label="Share reflection" class="w-11 h-11 flex items-center justify-center rounded-full text-on-surface-variant hover:text-primary hover:bg-surface-container transition-colors">
              <span class="material-symbols-outlined text-[20px]">share</span>
            </button>
            <div class="relative flex items-center justify-center p-0.5 rounded-full bg-surface-container ring-1 ring-secondary/20">
              <span class="material-symbols-outlined text-primary">person</span>
            </div>
          </div>
        </div>
      </header>
    `;
  }
  return `
    <header class="fixed top-0 inset-x-0 z-50 bg-surface/85 backdrop-blur-xl pt-safe shadow-[0_1px_12px_rgba(14,59,46,0.04)]">
      <div class="h-16 px-space-md flex items-center justify-between gap-space-sm">
        <div class="flex items-center gap-space-sm min-w-0">
          <img alt="QuranFlow Emblem Logo" class="h-8 w-auto object-contain shrink-0" src="https://lh3.googleusercontent.com/aida/AEtjO1UXcSMXmwXzqpHYydkhzU82UaqJNJtpyjLr5NmX6AA0XxAb2mPnEAouljylR41cqIhCtQVOTrgastVoW0LR-3muqnz87iZrQDsyt9yQwAhU0Yy7ydA5FS59sRhoyUVV6iCYRapB67jSC8rpSJy_JuFwwDZU1rmQztuY1x_4n5QyK7oNfSZuJRlrc7D4YnBDlLpnhGmEpo3hRWkUcnsPXzG4wKfqCu8SwMjRSzwe0XK1Sxl0Vp87WOMDmIUG"/>
          <div class="flex flex-col min-w-0">
            <div class="flex items-center gap-1.5">
              <span class="font-headline-sm text-headline-sm text-primary tracking-tight truncate">QuranFlow</span>
              <span class="inline-flex items-center px-1.5 py-0.5 rounded-full bg-secondary/10 text-secondary font-label-sm text-[10px] uppercase font-semibold tracking-wider">Daily</span>
            </div>
            <span class="font-label-sm text-label-sm text-on-surface-variant truncate">Daily Reminders</span>
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <button aria-label="Notifications" class="w-11 h-11 flex items-center justify-center rounded-full text-on-surface-variant hover:text-primary hover:bg-surface-container transition-colors relative">
            <span class="material-symbols-outlined text-[22px]">notifications</span>
          </button>
          <div class="relative flex items-center justify-center p-0.5 rounded-full bg-surface-container ring-1 ring-secondary/20 cursor-pointer" id="logout-trigger">
            <span class="material-symbols-outlined text-primary">person</span>
          </div>
        </div>
      </div>
    </header>
  `;
}

function navHtml(active, user) {
  const links = [
    { href: '#/dashboard', icon: 'auto_awesome', label: 'Today' },
    { href: '#/library',   icon: 'video_library', label: 'Library' },
    { href: '#/progress',  icon: 'trending_up', label: 'Progress' },
  ];
  if (user?.role === 'admin' || user?.role === 'curator') {
    links.push({ href: '#/admin', icon: 'tune', label: 'Curator' });
  }
  const li = links.map(l => `
    <a href="${l.href}" class="flex flex-col items-center justify-center min-w-[64px] h-12 gap-0.5 transition-all ${active === l.href ? 'text-primary font-bold' : 'text-on-surface-variant hover:text-primary'}" data-path="${l.label.toLowerCase()}">
      <span class="material-symbols-outlined text-[24px]">${l.icon}</span>
      <span class="font-label-sm text-label-sm leading-none">${l.label}</span>
    </a>
  `).join('');

  return `
    <nav class="fixed bottom-0 inset-x-0 z-50 pb-safe bg-surface/90 backdrop-blur-xl shadow-[0_-4px_20px_-2px_rgba(14,59,46,0.06)]">
      <div class="flex items-center justify-around h-16 px-2">
        ${li}
      </div>
    </nav>
  `;
}

function bindLogout(el) {
  el.querySelector('#logout-trigger')?.addEventListener('click', async () => {
    if(!confirm("Sign out?")) return;
    try { await API.post('/auth/logout'); } catch {}
    clearUser();
    navigate('/');
  });
}

function shell(active, user, innerHtml) {
  return `
    ${headerHtml(active, user)}
    <main class="flex flex-col relative w-full pt-16 pb-24 bg-surface min-h-[100dvh] h-[100dvh] overflow-y-auto">
      ${innerHtml}
    </main>
    ${navHtml(active, user)}
  `;
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
          <div class="form-group">
            <label for="gender">Gender</label>
            <select id="gender" required>
              <option value="" disabled selected>Select gender</option>
              <option value="Male">Male</option>
              <option value="Female">Female</option>
            </select>
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
        gender:           app.querySelector('#gender').value,
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

  app.innerHTML = shell('#/dashboard', user, `
    <div id="reminder-area" class="flex-1 w-full flex items-center justify-center p-0 sm:p-4">
      <div class="loading-overlay"><div class="spinner"></div></div>
    </div>
  `);
  bindLogout(app);

  const reminderResult = await API.get('/reminders/today').catch(e => e);

  const ra = app.querySelector('#reminder-area');
  if (reminderResult.id) {
    const v = reminderResult;
    ra.innerHTML = `
      <div class="relative w-full max-w-[480px] bg-black sm:rounded-[32px] overflow-hidden shadow-2xl flex flex-col justify-end mx-auto h-full max-h-full sm:h-auto sm:my-4 sm:aspect-[9/16] sm:max-h-[85vh]">
        <video id="dash-video" class="absolute inset-0 w-full h-full object-cover" controls preload="metadata" src="/api/v1/videos/${v.id}/stream"></video>
        
        <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent pt-32 pb-6 px-space-md flex flex-col justify-end pointer-events-none">
          <div class="pointer-events-auto">
            <div class="flex items-center gap-2 mb-2">
              <span class="inline-flex items-center px-2 py-0.5 rounded bg-surface/20 backdrop-blur-md text-surface font-label-md">✨ Fresh Today</span>
              ${v.category_name ? `<span class="inline-flex items-center px-2 py-0.5 rounded bg-surface/20 backdrop-blur-md text-surface font-label-md">${escHtml(v.category_name)}</span>` : ''}
              ${v.duration_seconds ? `<span class="inline-flex items-center px-2 py-0.5 rounded bg-surface/20 backdrop-blur-md text-surface font-label-md">⏱ ${fmtDuration(v.duration_seconds)}</span>` : ''}
            </div>
            
            <h2 class="text-surface font-display-lg-mobile mb-4 text-shadow-sm leading-tight">${escHtml(v.title)}</h2>
            
            <div class="flex items-center gap-space-sm">
              <button id="share-btn" data-id="${v.id}" class="flex-1 h-14 bg-primary text-on-primary rounded-full font-label-lg flex items-center justify-center gap-2 shadow-[0_8px_16px_rgba(0,36,26,0.2)] hover:bg-primary/90 transition-colors">
                <span class="material-symbols-outlined text-[20px]">send</span> Share
              </button>
              <button id="posted-btn" data-id="${v.id}" disabled class="flex-1 h-14 bg-surface/20 backdrop-blur-md text-surface rounded-full font-label-lg flex items-center justify-center gap-2 border border-surface/30 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-surface/30 transition-colors">
                <span class="material-symbols-outlined text-[20px]">check_circle</span> Posted
              </button>
            </div>
            
            <p id="posted-hint" class="text-surface/80 text-center font-label-sm mt-3">Share to WhatsApp to mark as posted</p>
          </div>
        </div>
      </div>
    `;
    bindShareAndPost(app, v.id, v.title);
  } else {
    const status = reminderResult.status;
    if (status === 404) {
      ra.innerHTML = `<div class="p-4 text-center mt-20"><div class="text-4xl mb-4">📭</div><p>No videos in the library yet. Check back soon!</p></div>`;
    } else {
      ra.innerHTML = `<div class="p-4 text-center mt-20"><p class="text-error">Could not load today's reminder: ${escHtml(reminderResult.message || 'Unknown error')}</p></div>`;
    }
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
      const safeTitle = (title || 'reminder').replace(/[^a-zA-Z0-9]/g, '_');
      const file  = new File([blob], `${safeTitle}.mp4`, { type: 'video/mp4' });

      if (navigator.canShare({ files: [file] })) {
        await navigator.share({
          files: [file],
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
      shareBtn.innerHTML = '<span>✅</span> Shared (Share Again)';
      shareBtn.disabled = false;
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
async function renderLibrary(app, categoryId = null, categoryName = null) {
  const user = await getUser();
  if (!user) { navigate('/login'); return; }

  if (!categoryId) {
    // Show Categories
    app.innerHTML = shell('#/library', user, `
      <div class="page-title">📚 Video Library</div>
      <p class="text-muted mb-16">Select a category to view videos.</p>
      <div id="categories-area"><div class="loading-overlay"><div class="spinner"></div></div></div>
    `);
    bindLogout(app);

    try {
      const cats = await API.get('/categories');
      if (cats.length === 0) {
        app.querySelector('#categories-area').innerHTML = `<div class="empty-state"><div class="empty-icon">📁</div><p>No categories found.</p></div>`;
      } else {
        const catHtml = cats.map(c => `
          <div class="card cat-card" style="cursor:pointer;" data-id="${c.id}" data-name="${escHtml(c.name)}">
            <h3 style="margin-top:0; color:var(--primary); font-size:1.2rem;">📁 ${escHtml(c.name)}</h3>
            <p class="text-muted" style="margin-bottom:0; font-size:0.9rem;">${escHtml(c.description || 'View videos in this category')}</p>
          </div>
        `).join('');
        app.querySelector('#categories-area').innerHTML = `<div class="video-grid" style="grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));">${catHtml}</div>`;
        
        app.querySelectorAll('.cat-card').forEach(card => {
          card.addEventListener('click', () => {
            renderLibrary(app, card.dataset.id, card.dataset.name);
          });
        });
      }
    } catch (err) {
      app.querySelector('#categories-area').innerHTML = `<div class="alert alert-error">${escHtml(err.message)}</div>`;
    }
  } else {
    // Show Videos for the selected category
    app.innerHTML = shell('#/library', user, `
      <div class="page-title" style="display:flex; align-items:center; gap:12px;">
        <button class="btn btn-secondary btn-sm" id="back-to-cats">&larr; Back</button>
        <span>📁 ${escHtml(categoryName)}</span>
      </div>
      <div class="search-bar">
        <input id="search-input" type="search" placeholder="Search videos in ${escHtml(categoryName)}…" />
      </div>
      <div id="videos-area"><div class="loading-overlay"><div class="spinner"></div></div></div>
      <div id="pagination-area"></div>
    `);
    bindLogout(app);

    app.querySelector('#back-to-cats').addEventListener('click', () => {
      renderLibrary(app, null, null);
    });

    let skip = 0, limit = 12, query = '';
    async function loadVideos() {
      const area = app.querySelector('#videos-area');
      area.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
      try {
        const params = new URLSearchParams({ skip, limit, category_id: categoryId });
        if (query) params.set('search', query);
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

    loadVideos();
  }
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
      shareBtn.textContent = '✅ Shared (Share Again)';
      shareBtn.disabled = false;
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
    <div class="px-space-md mt-6">
      <div class="flex items-end justify-between mb-space-sm">
        <h2 class="font-headline-lg text-headline-lg text-primary tracking-tight">Your Journey</h2>
      </div>
    </div>
    <div id="prog-area" class="px-space-md"><div class="loading-overlay"><div class="spinner"></div></div></div>
  `);
  bindLogout(app);

  try {
    const p = await API.get('/progress/weekly');
    app.querySelector('#prog-area').innerHTML = renderProgressWidget(p) + `
      <div class="mt-8">
        <h3 class="font-headline-md text-on-surface mb-4">Recent History</h3>
        <p class="text-on-surface-variant text-body-sm">Keep sharing daily reminders to build your streak. Only videos you mark as posted count.</p>
      </div>`;
  } catch (err) {
    app.querySelector('#prog-area').innerHTML = `<div class="p-4 bg-error-container text-on-error-container rounded-xl">${escHtml(err.message)}</div>`;
  }
}

function renderProgressWidget(p) {
  const pct = Math.round((p.total_posted / p.goal) * 100);
  
  // Weekly ring representation
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (pct / 100) * circumference;

  let daysHtml = '';
  const dayNames = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
  
  // simple mock for the days (assuming we just show 7 empty/filled circles)
  for (let i = 0; i < 7; i++) {
    const isPosted = i < p.total_posted;
    const isToday = i === p.total_posted; // basic highlight
    
    daysHtml += `
      <div class="flex flex-col items-center gap-1.5">
        <div class="w-8 h-8 rounded-full flex items-center justify-center transition-all ${isPosted ? 'bg-secondary text-on-secondary shadow-md scale-110 ring-2 ring-secondary/20' : isToday ? 'bg-surface-container ring-1 ring-outline text-on-surface' : 'bg-surface-container text-on-surface-variant'}">
          ${isPosted ? '<span class="material-symbols-outlined text-[16px]">check</span>' : '<span class="font-label-sm">'+dayNames[i][0]+'</span>'}
        </div>
        <span class="font-label-sm text-[10px] ${isToday ? 'text-primary font-bold' : 'text-on-surface-variant'}">${dayNames[i]}</span>
      </div>`;
  }

  return `
    <div class="bg-surface-container-lowest rounded-3xl p-space-md shadow-[0_8px_24px_rgba(14,59,46,0.08)] ring-1 ring-surface-container-highest relative overflow-hidden">
      <!-- Decorative background element -->
      <div class="absolute -right-12 -top-12 w-40 h-40 bg-secondary-fixed/30 rounded-full blur-3xl mix-blend-multiply"></div>
      
      <div class="flex items-center gap-space-md relative z-10">
        <!-- Circular Progress Ring -->
        <div class="relative w-24 h-24 shrink-0 flex items-center justify-center">
          <svg class="w-full h-full transform -rotate-90" viewBox="0 0 80 80">
            <circle class="text-surface-container-highest stroke-current" cx="40" cy="40" r="36" stroke-width="6" fill="transparent"></circle>
            <circle class="text-primary stroke-current transition-all duration-1000 ease-out" cx="40" cy="40" r="36" stroke-width="6" fill="transparent" stroke-linecap="round" stroke-dasharray="${circumference}" stroke-dashoffset="${strokeDashoffset}"></circle>
          </svg>
          <div class="absolute inset-0 flex flex-col items-center justify-center">
            <span class="font-headline-md text-primary leading-none mb-0.5">${p.total_posted}<span class="text-body-sm text-on-surface-variant font-normal">/${p.goal}</span></span>
            <span class="font-label-sm text-[10px] text-on-surface-variant uppercase tracking-wider">Days</span>
          </div>
        </div>
        
        <div class="flex flex-col">
          <h3 class="font-headline-sm text-on-surface mb-1">Weekly Goal</h3>
          <p class="font-body-sm text-on-surface-variant leading-relaxed">You've shared ${p.total_posted} reminders this week. Keep up the momentum!</p>
        </div>
      </div>
      
      <!-- 7-Day Tracker -->
      <div class="mt-6 pt-5 border-t border-surface-container-highest">
        <div class="flex justify-between items-end px-1 relative z-10">
          ${daysHtml}
        </div>
      </div>
    </div>
  `;
}


/* ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ */
/* HISTORY                                                                    */
/* ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ */
async function renderHistory(app) {
  const user = await getUser();
  if (!user) { navigate('/login'); return; }

  app.innerHTML = shell('#/history', user, `
    <div class="page-title">≡ƒôï Posting History</div>
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
        area.innerHTML = `<div class="empty-state"><div class="empty-icon">≡ƒô¡</div><p>No posting history yet.<br>Share a reminder to get started!</p></div>`;
      } else {
        area.innerHTML = data.items.map(item => `
          <div class="history-item">
            <div class="history-thumb">≡ƒÄ¼</div>
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
      <div style="margin-bottom: 16px;">
        <button class="btn btn-secondary btn-sm" id="dl-csv-btn">📥 Download CSV</button>
      </div>
      <div id="users-area"><div class="loading-overlay"><div class="spinner"></div></div></div>
    </div>` : ''}
  `);
  bindLogout(app);

  const dlBtn = app.querySelector('#dl-csv-btn');
  if (dlBtn) {
    dlBtn.addEventListener('click', () => {
      window.open('/api/v1/admin/users/csv', '_blank');
    });
  }

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
    async function loadUsers() {
      try {
        const users = await API.get('/admin/users');
        const tbody = users.map(u => `
          <tr>
            <td>${escHtml(u.display_name)}</td>
            <td>${escHtml(u.email)}</td>
            <td>${escHtml(u.gender || '-')}</td>
            <td><span class="role-badge role-${u.role}">${u.role}</span></td>
            <td>${u.is_active ? '✅' : '❌'}</td>
            <td class="text-muted">${fmtDate(u.created_at)}</td>
            <td>
              <button class="btn btn-secondary btn-sm edit-u" data-id="${u.id}" data-role="${u.role}" data-active="${u.is_active}">Edit</button>
              <button class="btn btn-danger btn-sm del-u" data-id="${u.id}">Del</button>
            </td>
          </tr>`).join('');
        app.querySelector('#users-area').innerHTML = `
          <table class="users-table">
            <thead><tr><th>Name</th><th>Email</th><th>Gender</th><th>Role</th><th>Active</th><th>Joined</th><th>Actions</th></tr></thead>
            <tbody>${tbody}</tbody>
          </table>`;

        app.querySelectorAll('.edit-u').forEach(b => b.addEventListener('click', async () => {
          const newRole = prompt('Enter new role (user, curator, admin):', b.dataset.role);
          if (!newRole) return;
          const isActive = confirm('Should this user be active? (OK = yes, Cancel = no)');
          b.disabled = true;
          try {
            await API.patch(`/admin/users/${b.dataset.id}`, { role: newRole, is_active: isActive });
            loadUsers();
          } catch (e) { alert(e.message); b.disabled = false; }
        }));

        app.querySelectorAll('.del-u').forEach(b => b.addEventListener('click', async () => {
          if (!confirm('Are you sure you want to delete this user?')) return;
          b.disabled = true;
          try {
            await API.delete(`/admin/users/${b.dataset.id}`);
            loadUsers();
          } catch (e) { alert(e.message); b.disabled = false; }
        }));
      } catch (err) {
        app.querySelector('#users-area').innerHTML = `<div class="alert alert-error">${escHtml(err.message)}</div>`;
      }
    }
    loadUsers();
  }
}

