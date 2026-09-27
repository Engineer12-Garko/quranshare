import re

app_js_path = r"app\static\js\app.js"

with open(app_js_path, "r", encoding="utf-8") as f:
    content = f.read()

new_lib = r"""async function renderLibrary(app) {
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
}"""

content = re.sub(r'async function renderLibrary\(app,.*?\}\n(?=\s*(?:/\*\s+──\s+Library\s+Item|function videoCard))', new_lib + '\n\n', content, flags=re.DOTALL)

with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(content)
