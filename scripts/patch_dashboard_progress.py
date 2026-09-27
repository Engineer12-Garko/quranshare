import re

app_js_path = r"app\static\js\app.js"

with open(app_js_path, "r", encoding="utf-8") as f:
    content = f.read()

# DASHBOARD REPLACEMENT
dashboard_code = r"""
async function renderDashboard(app) {
  const user = await getUser();
  if (!user) { navigate('/login'); return; }

  app.innerHTML = shell('#/dashboard', user, `
    <div id="reminder-area" class="h-full w-full flex items-center justify-center">
      <div class="loading-overlay"><div class="spinner"></div></div>
    </div>
  `);
  bindLogout(app);

  const reminderResult = await API.get('/reminders/today').catch(e => e);

  const ra = app.querySelector('#reminder-area');
  if (reminderResult.id) {
    const v = reminderResult;
    ra.innerHTML = `
      <div class="relative w-full max-w-[480px] aspect-[9/16] bg-black sm:rounded-[32px] overflow-hidden shadow-2xl flex flex-col justify-end mx-auto my-auto sm:my-4 h-full sm:h-auto sm:max-h-[85vh]">
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
"""

content = re.sub(r"async function renderDashboard\(app\) \{.*?(?=/\* ── Core share helper)", dashboard_code.strip() + "\n\n", content, flags=re.DOTALL)


# PROGRESS REPLACEMENT
progress_code = r"""
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
"""

content = re.sub(r"async function renderProgress\(app\) \{.*?(?=\n/\* ══════════════════════════════════════════════════════════════════════════ \*/\n/\* PROFILE)", progress_code.strip() + "\n", content, flags=re.DOTALL)


with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(content)
