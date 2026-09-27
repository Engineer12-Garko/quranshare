import re

app_js_path = r"app\static\js\app.js"

with open(app_js_path, "r", encoding="utf-8") as f:
    content = f.read()

nav_html = r"""
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
    <main class="flex flex-col relative w-full pt-16 pb-24 bg-surface min-h-screen">
      ${innerHtml}
    </main>
    ${navHtml(active, user)}
  `;
}
"""

content = re.sub(r"/\* ── Nav HTML ──.*?function shell\(active, user, innerHtml\) \{.*?\n\}", nav_html.strip(), content, flags=re.DOTALL)

with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(content)
