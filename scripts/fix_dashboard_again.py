import re

app_js_path = r"app\static\js\app.js"

with open(app_js_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix Dashboard Responsiveness
# We want the video card to be smaller ("medium") and the buttons to be clearly BELOW the video.
dashboard_patch = r"""
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
    const v = res.video;
    
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
          
          <!-- Floating Video Metadata overlay -->
          <div class="absolute bottom-0 inset-x-0 p-4 bg-gradient-to-t from-black/90 via-black/40 to-transparent pointer-events-none">
            <div class="flex flex-wrap items-center gap-1.5 mb-1.5">
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-[10px] font-bold shadow-sm">
                <span class="material-symbols-outlined text-[12px]">auto_awesome</span> Fresh Today
              </span>
              ${v.category_name ? `<span class="inline-flex items-center px-2 py-0.5 rounded bg-surface/20 backdrop-blur-md text-surface font-label-sm text-[10px]">${escHtml(v.category_name)}</span>` : ''}
              ${v.duration_seconds ? `<span class="inline-flex items-center px-2 py-0.5 rounded bg-surface/20 backdrop-blur-md text-surface font-label-sm text-[10px]">⏱ ${fmtDuration(v.duration_seconds)}</span>` : ''}
            </div>
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
"""

content = re.sub(r'async function renderDashboard\(app\) \{[\s\S]*?\}\n\s*(?=/\* ── Core share helper)', dashboard_patch.strip() + '\n\n', content)

with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(content)
