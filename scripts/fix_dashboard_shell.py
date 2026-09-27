import re

app_js_path = r"app\static\js\app.js"

with open(app_js_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Dashboard UI Fixes
# Currently, the video and buttons are overlapping.
# The user wants buttons BELOW the video.
# Original Dashboard render:
dashboard_patch = r"""
async function renderDashboard(app) {
  const user = await getUser();
  if (!user) { navigate('/login'); return; }

  app.innerHTML = shell('#/dashboard', user, `
    <div id="reminder-area" class="flex-1 w-full flex items-center justify-center p-0 sm:p-4">
      <div class="loading-overlay"><div class="spinner"></div></div>
    </div>
  `);
  bindLogout(app);

  try {
    const res = await API.get('/reminders/today');
    const v = res.video;
    
    // Video Card with Buttons BELOW the video
    const videoHtml = `
      <div class="relative w-full max-w-[480px] bg-surface-container sm:rounded-[32px] overflow-hidden shadow-2xl flex flex-col mx-auto h-full max-h-full sm:h-auto sm:my-4 sm:max-h-[85vh]">
        
        <!-- Video Container (Flex-1 to take available space) -->
        <div class="relative flex-1 w-full bg-black flex items-center justify-center overflow-hidden">
          <video 
            id="today-video"
            src="/api/v1/videos/${v.id}/stream" 
            class="absolute inset-0 w-full h-full object-cover"
            controls 
            autoplay 
            playsinline 
            preload="metadata"
            loop
          ></video>
          
          <!-- Floating Video Metadata overlay -->
          <div class="absolute bottom-0 inset-x-0 p-6 bg-gradient-to-t from-black/80 via-black/40 to-transparent pointer-events-none">
            <div class="flex items-center gap-2 mb-2">
              <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-[11px] font-bold tracking-wide shadow-sm">
                <span class="material-symbols-outlined text-[14px]">auto_awesome</span> Fresh Today
              </span>
            </div>
            <h2 class="font-headline-sm text-white drop-shadow-md leading-snug">${escHtml(v.title)}</h2>
            ${v.description ? `<p class="mt-2 text-white/90 font-body-sm line-clamp-2 drop-shadow-sm">${escHtml(v.description)}</p>` : ''}
          </div>
        </div>
        
        <!-- Actions Container (BELOW the video) -->
        <div class="w-full bg-surface-container-high p-4 flex gap-3 shrink-0">
          <button id="btn-share" class="flex-1 h-12 flex items-center justify-center gap-2 rounded-xl bg-primary text-on-primary font-label-lg hover:bg-primary/90 transition-colors shadow-sm" data-id="${v.id}">
            <span class="material-symbols-outlined text-[20px]">send</span> Share
          </button>
          <button id="btn-posted" class="flex-1 h-12 flex items-center justify-center gap-2 rounded-xl bg-surface-container-highest text-on-surface hover:bg-surface-dim transition-colors" data-id="${v.id}">
            <span class="material-symbols-outlined text-[20px]">check_circle</span> Mark Posted
          </button>
        </div>
      </div>
    `;
    
    app.querySelector('#reminder-area').innerHTML = videoHtml;

    // Add interactivity logic
    const shareBtn = app.querySelector('#btn-share');
    const postedBtn = app.querySelector('#btn-posted');

    shareBtn.addEventListener('click', async () => {
      shareBtn.disabled = true; shareBtn.innerHTML = '<span class="material-symbols-outlined text-[20px] animate-spin">sync</span> Preparing...';
      try { await API.post(`/videos/${v.id}/share`); } catch {}
      const shared = await shareVideoFile(v.id, v.title, null);
      shareBtn.disabled = false;
      if (shared) {
        shareBtn.innerHTML = '<span class="material-symbols-outlined text-[20px]">send</span> Share Again';
      } else {
        shareBtn.innerHTML = '<span class="material-symbols-outlined text-[20px]">send</span> Share';
      }
    });

    postedBtn.addEventListener('click', async () => {
      postedBtn.disabled = true; postedBtn.innerHTML = '<span class="material-symbols-outlined text-[20px] animate-spin">sync</span> Saving...';
      try {
        await API.post(`/videos/${v.id}/posted`);
        postedBtn.innerHTML = '<span class="material-symbols-outlined text-[20px]">done_all</span> Posted!';
        postedBtn.classList.add('bg-secondary', 'text-on-secondary');
        postedBtn.classList.remove('bg-surface-container-highest', 'text-on-surface');
      } catch (err) {
        alert(err.message);
        postedBtn.disabled = false;
        postedBtn.innerHTML = '<span class="material-symbols-outlined text-[20px]">check_circle</span> Mark Posted';
      }
    });

  } catch (err) {
    if (err.status === 404) {
      app.querySelector('#reminder-area').innerHTML = `
        <div class="max-w-md w-full p-8 text-center bg-surface-container rounded-3xl shadow-sm border border-surface-container-highest">
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
"""

content = re.sub(r'async function renderDashboard\(app\) \{.*?\}\n(?=/\* ── Core share helper)', dashboard_patch.strip() + '\n\n', content, flags=re.DOTALL)


# 2. Responsive Shell Fixes
# Desktop: Side Navigation Panel
# Mobile: Bottom Navigation Bar
shell_patch = r"""
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
"""

content = re.sub(r'function headerHtml\(active, user\).*?(?=/\* ── Core share helper)', shell_patch.strip() + '\n\n', content, flags=re.DOTALL)

with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(content)
