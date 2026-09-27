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
  // Hide top header on desktop (sm:hidden)
  return `
    <header class="sm:hidden fixed top-0 inset-x-0 z-50 bg-surface/85 backdrop-blur-xl pt-safe shadow-[0_1px_12px_rgba(14,59,46,0.04)]">
      <div class="h-16 px-space-md flex items-center justify-between gap-space-sm">
        <div class="flex items-center gap-space-sm min-w-0">
          <img alt="QuranFlow" class="h-8 w-auto object-contain shrink-0" src="https://lh3.googleusercontent.com/aida/AEtjO1UXcSMXmwXzqpHYydkhzU82UaqJNJtpyjLr5NmX6AA0XxAb2mPnEAouljylR41cqIhCtQVOTrgastVoW0LR-3muqnz87iZrQDsyt9yQwAhU0Yy7ydA5FS59sRhoyUVV6iCYRapB67jSC8rpSJy_JuFwwDZU1rmQztuY1x_4n5QyK7oNfSZuJRlrc7D4YnBDlLpnhGmEpo3hRWkUcnsPXzG4wKfqCu8SwMjRSzwe0XK1Sxl0Vp87WOMDmIUG"/>
          <span class="font-headline-sm text-primary tracking-tight">QuranFlow</span>
        </div>
        <div class="relative flex items-center justify-center p-0.5 rounded-full bg-surface-container ring-1 ring-secondary/20 cursor-pointer" id="logout-trigger-mobile">
          <span class="material-symbols-outlined text-primary">person</span>
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
  
  // Mobile Bottom Nav
  const mobileLi = links.map(l => `
    <a href="${l.href}" class="flex flex-col items-center justify-center min-w-[64px] h-12 gap-0.5 transition-all ${active === l.href ? 'text-primary font-bold' : 'text-on-surface-variant hover:text-primary'}">
      <span class="material-symbols-outlined text-[24px]">${l.icon}</span>
      <span class="font-label-sm text-label-sm leading-none">${l.label}</span>
    </a>
  `).join('');

  // Desktop Side Nav
  const desktopLi = links.map(l => `
    <a href="${l.href}" class="flex items-center gap-4 px-4 py-3 rounded-xl transition-all ${active === l.href ? 'bg-primary-container text-on-primary-container font-bold' : 'text-on-surface-variant hover:bg-surface-container hover:text-primary'}">
      <span class="material-symbols-outlined text-[24px]">${l.icon}</span>
      <span class="font-label-lg">${l.label}</span>
    </a>
  `).join('');

  return `
    <!-- Mobile Bottom Nav -->
    <nav class="sm:hidden fixed bottom-0 inset-x-0 z-50 pb-safe bg-surface/90 backdrop-blur-xl shadow-[0_-4px_20px_-2px_rgba(14,59,46,0.06)]">
      <div class="flex items-center justify-around h-16 px-2">
        ${mobileLi}
      </div>
    </nav>
    
    <!-- Desktop Side Nav -->
    <aside class="hidden sm:flex fixed top-0 left-0 bottom-0 w-64 bg-surface border-r border-surface-container flex-col z-50">
      <div class="p-6 flex items-center gap-3">
        <img alt="QuranFlow" class="h-10 w-auto object-contain" src="https://lh3.googleusercontent.com/aida/AEtjO1UXcSMXmwXzqpHYydkhzU82UaqJNJtpyjLr5NmX6AA0XxAb2mPnEAouljylR41cqIhCtQVOTrgastVoW0LR-3muqnz87iZrQDsyt9yQwAhU0Yy7ydA5FS59sRhoyUVV6iCYRapB67jSC8rpSJy_JuFwwDZU1rmQztuY1x_4n5QyK7oNfSZuJRlrc7D4YnBDlLpnhGmEpo3hRWkUcnsPXzG4wKfqCu8SwMjRSzwe0XK1Sxl0Vp87WOMDmIUG"/>
        <h1 class="font-headline-md text-primary tracking-tight">QuranFlow</h1>
      </div>
      <div class="flex-1 px-4 flex flex-col gap-2">
        ${desktopLi}
      </div>
      <div class="p-4 border-t border-surface-container">
        <button id="logout-trigger-desktop" class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-error hover:bg-error-container transition-colors">
          <span class="material-symbols-outlined">logout</span>
          <span class="font-label-lg">Sign Out</span>
        </button>
      </div>
    </aside>
  `;
}

function bindLogout(el) {
  const handler = async () => {
    if(!confirm("Sign out?")) return;
    try { await API.post('/auth/logout'); } catch {}
    clearUser();
    navigate('/');
  };
  el.querySelector('#logout-trigger-mobile')?.addEventListener('click', handler);
  el.querySelector('#logout-trigger-desktop')?.addEventListener('click', handler);
}

function shell(active, user, innerHtml) {
  return `
    ${headerHtml(active, user)}
    ${navHtml(active, user)}
    <!-- Main content container dynamically adjusts layout based on screen size -->
    <main class="flex flex-col relative w-full bg-surface min-h-[100dvh] h-[100dvh] overflow-y-auto pt-16 pb-24 sm:pt-0 sm:pb-0 sm:pl-64">
      ${innerHtml}
    </main>
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
    <div id="reminder-area" class="flex-1 w-full flex items-center justify-center p-4">
      <div class="loading-overlay"><div class="spinner"></div></div>
    </div>
  `);
  bindLogout(app);

  try {
    const res = await API.get('/reminders/today');
    const v = res;
    
    // Medium sized card with buttons BELOW
    const videoHtml = `
      <div class="w-full max-w-[360px] bg-surface-container rounded-3xl overflow-hidden shadow-xl flex flex-col mx-auto my-auto border border-surface-container-highest">
        
        <!-- Video Container -->
        <div class="relative w-full aspect-[4/5] bg-black flex items-center justify-center overflow-hidden shrink-0">
          <video 
            id="today-video"
            src="/api/v1/videos/${v.id}/stream" 
            class="absolute inset-0 w-full h-full object-cover"
            controls 
            preload="metadata"
          ></video>
          
          <!-- Top Badges Overlay -->
          <div class="absolute top-0 inset-x-0 p-4 bg-gradient-to-b from-black/80 to-transparent pointer-events-none flex flex-wrap items-start gap-1.5">
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-[10px] font-bold shadow-sm">
              <span class="material-symbols-outlined text-[12px]">auto_awesome</span> Fresh Today
            </span>
            ${v.category_name ? `<span class="inline-flex items-center px-2 py-0.5 rounded bg-surface/20 backdrop-blur-md text-surface font-label-sm text-[10px]">${escHtml(v.category_name)}</span>` : ''}
            ${v.duration_seconds ? `<span class="inline-flex items-center px-2 py-0.5 rounded bg-surface/20 backdrop-blur-md text-surface font-label-sm text-[10px]">⏱ ${fmtDuration(v.duration_seconds)}</span>` : ''}
          </div>
          
          <!-- Bottom Metadata overlay -->
          <div class="absolute bottom-0 inset-x-0 p-4 bg-gradient-to-t from-black/90 via-black/40 to-transparent pointer-events-none">
            <h2 class="font-headline-sm text-white drop-shadow-md leading-tight">${escHtml(v.title)}</h2>
            ${v.description ? `<p class="mt-1 text-white/90 font-body-sm text-[11px] line-clamp-2 drop-shadow-sm">${escHtml(v.description)}</p>` : ''}
          </div>
        </div>
        
        <!-- Actions Container (BELOW the video) -->
        <div class="w-full bg-surface-container-high p-3 flex gap-2 shrink-0 border-t border-surface-container-highest">
          <button id="btn-share" class="flex-1 h-11 flex items-center justify-center gap-2 rounded-xl bg-primary text-on-primary font-label-md hover:bg-primary/90 transition-colors shadow-sm" data-id="${v.id}">
            <span class="material-symbols-outlined text-[18px]">send</span> Share
          </button>
          <button id="btn-posted" class="flex-1 h-11 flex items-center justify-center gap-2 rounded-xl bg-surface-container-highest text-on-surface hover:bg-surface-dim transition-colors border border-outline-variant/30" data-id="${v.id}">
            <span class="material-symbols-outlined text-[18px]">check_circle</span> Posted
          </button>
        </div>
      </div>
    `;
    
    app.querySelector('#reminder-area').innerHTML = videoHtml;

    // Add interactivity logic
    const shareBtn = app.querySelector('#btn-share');
    const postedBtn = app.querySelector('#btn-posted');

    shareBtn.addEventListener('click', async () => {
      shareBtn.disabled = true; shareBtn.innerHTML = '<span class="material-symbols-outlined text-[18px] animate-spin">sync</span> ...';
      try { await API.post(`/videos/${v.id}/share`); } catch {}
      const shared = await shareVideoFile(v.id, v.title, null);
      shareBtn.disabled = false;
      if (shared) {
        shareBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">send</span> Shared!';
      } else {
        shareBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">send</span> Share';
      }
    });

    postedBtn.addEventListener('click', async () => {
      postedBtn.disabled = true; postedBtn.innerHTML = '<span class="material-symbols-outlined text-[18px] animate-spin">sync</span> ...';
      try {
        await API.post(`/videos/${v.id}/posted`);
        postedBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">done_all</span> Posted!';
        postedBtn.classList.add('bg-secondary', 'text-on-secondary');
        postedBtn.classList.remove('bg-surface-container-highest', 'text-on-surface');
      } catch (err) {
        alert(err.message);
        postedBtn.disabled = false;
        postedBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">check_circle</span> Posted';
      }
    });

  } catch (err) {
    if (err.status === 404) {
      app.querySelector('#reminder-area').innerHTML = `
        <div class="max-w-sm w-full p-8 text-center bg-surface-container rounded-3xl shadow-sm border border-surface-container-highest">
          <div class="w-16 h-16 mx-auto mb-4 bg-secondary-container rounded-full flex items-center justify-center">
            <span class="material-symbols-outlined text-on-secondary-container text-[32px]">task_alt</span>
          </div>
          <h2 class="font-headline-md text-on-surface mb-2">You're all caught up!</h2>
          <p class="font-body-md text-on-surface-variant mb-6">You've shared all your reminders for today. Check back tomorrow for a fresh one.</p>
          <a href="#/library" class="inline-flex h-12 items-center justify-center px-6 rounded-full bg-primary text-on-primary font-label-lg hover:bg-primary/90 transition-colors">
            Browse Library
          </a>
        </div>
      `;
    } else {
      app.querySelector('#reminder-area').innerHTML = `<div class="p-4 bg-error-container text-on-error-container rounded-xl shadow-sm">${escHtml(err.message)}</div>`;
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
async function renderLibrary(app) {
  const user = await getUser();
  if (!user) { navigate('/login'); return; }

  app.innerHTML = shell('#/library', user, `
    <!-- Top Search Bar -->
    <div class="px-space-md py-4 bg-surface sticky top-16 z-40 border-b border-surface-container shadow-sm sm:top-0">
      <div class="relative max-w-3xl mx-auto">
        <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant">search</span>
        <input type="text" id="search-input" placeholder="Search by topic, surah, or emotion..." class="w-full h-12 pl-10 pr-4 bg-surface-container-low border border-outline-variant rounded-full font-body-md text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all shadow-sm">
      </div>
    </div>

    <!-- Content Area -->
    <div class="flex-1 overflow-y-auto px-space-md py-6">
      <!-- Videos Section -->
      <div class="max-w-6xl mx-auto">
        <h2 class="font-headline-sm text-primary mb-4 flex items-center justify-between" id="video-section-title">
          <span class="flex items-center gap-2"><span class="material-symbols-outlined text-[20px]">video_library</span> All Reminders</span>
        </h2>
        <div id="lib-area"><div class="loading-overlay"><div class="spinner"></div></div></div>
        <div id="lib-pagination" class="mt-8 flex justify-center pb-8"></div>
      </div>
    </div>
  `);
  bindLogout(app);

  let query = '';
  let skip = 0;
  const limit = 12;
  let searchTimer;

  async function loadVideos() {
    const la = app.querySelector('#lib-area');
    la.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
    try {
      const qs = new URLSearchParams({ skip, limit });
      if (query) qs.set('search', query);
      
      const res = await API.get('/videos?' + qs.toString());
      if (res.items.length === 0) {
        la.innerHTML = `<div class="p-8 text-center bg-surface-container rounded-2xl border border-surface-container-highest max-w-md mx-auto mt-8"><span class="material-symbols-outlined text-[48px] text-outline mb-2">search_off</span><p class="font-body-md text-on-surface-variant">No videos found.</p></div>`;
        app.querySelector('#lib-pagination').innerHTML = '';
        return;
      }
      la.innerHTML = `<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-space-md" id="lib-grid"></div>`;
      const grid = la.querySelector('#lib-grid');
      res.items.forEach(v => grid.insertAdjacentHTML('beforeend', videoCard(v)));
      bindVideoCards(grid);
      renderPagination(app.querySelector('#lib-pagination'), res.total, skip, limit, s => { skip = s; loadVideos(); });
    } catch (err) {
      la.innerHTML = `<div class="p-4 bg-error-container text-on-error-container rounded-xl">${escHtml(err.message)}</div>`;
    }
  }

  app.querySelector('#search-input').addEventListener('input', e => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { query = e.target.value.trim(); skip = 0; loadVideos(); }, 350);
  });

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
    
    app.querySelector('#download-csv-btn')?.addEventListener('click', async () => {
      const btn = app.querySelector('#download-csv-btn');
      btn.innerHTML = '<span class="material-symbols-outlined text-[18px] animate-spin">sync</span> Downloading...';
      try {
        const token = localStorage.getItem('token');
        const resp = await fetch('/api/v1/admin/users/csv', { headers: { 'Authorization': `Bearer ${token}` } });
        if (!resp.ok) throw new Error("Failed to export CSV");
        const blob = await resp.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "users_export.csv";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } catch (e) {
        alert(e.message);
      }
      btn.innerHTML = '<span class="material-symbols-outlined text-[18px]">download</span> Export CSV';
    });
    
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

