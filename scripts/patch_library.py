import re

app_js_path = r"app\static\js\app.js"

with open(app_js_path, "r", encoding="utf-8") as f:
    content = f.read()

library_code = r"""
async function renderLibrary(app) {
  const user = await getUser();
  if (!user) { navigate('/login'); return; }

  app.innerHTML = shell('#/library', user, `
    <!-- Top Search Bar & Filters -->
    <div class="px-space-md py-4 bg-surface sticky top-16 z-40 border-b border-surface-container shadow-sm">
      <div class="relative">
        <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant">search</span>
        <input type="text" id="search-input" placeholder="Search by topic, surah, or emotion..." class="w-full h-12 pl-10 pr-4 bg-surface-container-low border border-outline-variant rounded-full font-body-md text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all">
      </div>
      
      <!-- Filter Chips -->
      <div class="flex overflow-x-auto gap-2 mt-4 pb-1 -mx-space-md px-space-md scrollbar-hide" id="category-chips">
        <button class="shrink-0 h-8 px-4 rounded-full font-label-md transition-colors bg-primary text-on-primary shadow-sm" data-cat="">All</button>
        <button class="shrink-0 h-8 px-4 rounded-full font-label-md transition-colors bg-surface-container border border-outline-variant text-on-surface hover:bg-surface-container-high">Quran</button>
        <button class="shrink-0 h-8 px-4 rounded-full font-label-md transition-colors bg-surface-container border border-outline-variant text-on-surface hover:bg-surface-container-high">Dua</button>
        <button class="shrink-0 h-8 px-4 rounded-full font-label-md transition-colors bg-surface-container border border-outline-variant text-on-surface hover:bg-surface-container-high">Sabr</button>
      </div>
    </div>

    <!-- Content Area -->
    <div class="flex-1 overflow-y-auto px-space-md py-6">
      
      <!-- Categories Section (Bento Grid style) -->
      <div class="mb-8" id="categories-section">
        <h2 class="font-headline-sm text-primary mb-4 flex items-center gap-2">
          <span class="material-symbols-outlined text-[20px]">grid_view</span> Browse Collections
        </h2>
        <div class="grid grid-cols-2 gap-3" id="categories-grid">
          <!-- Categories injected here -->
        </div>
      </div>

      <!-- Videos Section -->
      <div>
        <h2 class="font-headline-sm text-primary mb-4 flex items-center justify-between" id="video-section-title">
          <span class="flex items-center gap-2"><span class="material-symbols-outlined text-[20px]">video_library</span> All Reminders</span>
        </h2>
        <div id="lib-area"><div class="loading-overlay"><div class="spinner"></div></div></div>
        <div id="lib-pagination" class="mt-6 flex justify-center"></div>
      </div>
    </div>
  `);
  bindLogout(app);

  let query = '';
  let skip = 0;
  const limit = 12;
  let activeCategoryId = '';
  let searchTimer;

  async function loadCategories() {
    try {
      const cats = await API.get('/categories');
      const cg = app.querySelector('#categories-grid');
      const chips = app.querySelector('#category-chips');
      
      let gridHtml = '';
      let chipsHtml = `<button class="shrink-0 h-8 px-4 rounded-full font-label-md transition-colors ${activeCategoryId === '' ? 'bg-primary text-on-primary shadow-sm' : 'bg-surface-container border border-outline-variant text-on-surface hover:bg-surface-container-high'}" data-cat="">All</button>`;
      
      cats.forEach((c, idx) => {
        // Create 2-col bento grid with first item spanning full width
        const isFeatured = idx === 0;
        const colSpan = isFeatured ? 'col-span-2 aspect-[2.5/1]' : 'col-span-1 aspect-[4/3]';
        
        gridHtml += `
          <button class="cat-btn relative ${colSpan} rounded-2xl overflow-hidden group text-left shadow-sm ring-1 ring-surface-container-highest transition-all hover:shadow-md hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-primary" data-id="${c.id}" data-name="${escHtml(c.name)}">
            <div class="absolute inset-0 bg-gradient-to-br from-primary/90 to-tertiary/90 p-4 flex flex-col justify-end">
              <h3 class="font-headline-sm text-on-primary mb-0.5">${escHtml(c.name)}</h3>
              <p class="font-label-sm text-primary-fixed-dim">${c.video_count || 0} videos</p>
            </div>
          </button>
        `;
        
        chipsHtml += `<button class="shrink-0 h-8 px-4 rounded-full font-label-md transition-colors ${activeCategoryId === c.id ? 'bg-primary text-on-primary shadow-sm' : 'bg-surface-container border border-outline-variant text-on-surface hover:bg-surface-container-high'}" data-cat="${c.id}">${escHtml(c.name)}</button>`;
      });
      cg.innerHTML = gridHtml;
      chips.innerHTML = chipsHtml;
      
      // Bind click handlers
      app.querySelectorAll('.cat-btn, #category-chips button').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const btnData = e.currentTarget.dataset;
          activeCategoryId = btnData.id !== undefined ? btnData.id : btnData.cat;
          skip = 0;
          app.querySelector('#video-section-title').innerHTML = activeCategoryId 
            ? `<span class="flex items-center gap-2"><span class="material-symbols-outlined text-[20px]">folder_open</span> ${escHtml(btnData.name || 'Category')}</span> <button id="clear-cat" class="text-label-sm text-primary underline">Clear</button>` 
            : `<span class="flex items-center gap-2"><span class="material-symbols-outlined text-[20px]">video_library</span> All Reminders</span>`;
            
          if (app.querySelector('#clear-cat')) {
            app.querySelector('#clear-cat').addEventListener('click', () => {
              activeCategoryId = ''; skip = 0;
              loadCategories(); // refresh active chip state
              loadVideos();
            });
          }
          
          loadCategories(); // Refresh chips
          loadVideos();
          // Scroll to videos
          app.querySelector('#video-section-title').scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
      });
    } catch (e) {
      console.error("Failed to load categories", e);
    }
  }

  async function loadVideos() {
    const la = app.querySelector('#lib-area');
    la.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';
    try {
      const qs = new URLSearchParams({ skip, limit });
      if (query) qs.set('q', query);
      if (activeCategoryId) qs.set('category_id', activeCategoryId);
      
      const res = await API.get('/videos?' + qs.toString());
      if (res.items.length === 0) {
        la.innerHTML = `<div class="p-8 text-center bg-surface-container rounded-2xl border border-surface-container-highest"><span class="material-symbols-outlined text-[48px] text-outline mb-2">search_off</span><p class="font-body-md text-on-surface-variant">No videos found.</p></div>`;
        app.querySelector('#lib-pagination').innerHTML = '';
        return;
      }
      la.innerHTML = `<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-space-md" id="lib-grid"></div>`;
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

  loadCategories();
  loadVideos();
}

function videoCard(v) {
  return `
    <div class="video-card bg-surface-container-lowest border border-surface-container-highest rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow group flex flex-col" data-id="${v.id}">
      <!-- Placeholder for Video Thumbnail (Since we stream, we might not have one, using a generated pattern or title snippet) -->
      <div class="aspect-[16/9] bg-surface-container flex items-center justify-center relative overflow-hidden">
        <span class="material-symbols-outlined text-[48px] text-surface-container-highest/50 absolute">play_circle</span>
        <div class="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
        <div class="absolute bottom-2 left-2 flex gap-1">
          ${v.duration_seconds ? `<span class="bg-black/60 backdrop-blur-sm text-white font-label-sm text-[10px] px-1.5 py-0.5 rounded">${fmtDuration(v.duration_seconds)}</span>` : ''}
        </div>
      </div>
      
      <div class="p-3 flex flex-col flex-1">
        <div class="font-headline-sm text-sm text-on-surface line-clamp-2 leading-tight mb-1 group-hover:text-primary transition-colors">${escHtml(v.title)}</div>
        <div class="flex items-center text-xs text-on-surface-variant font-label-sm mt-auto">
          ${v.category_name ? `<span class="truncate bg-surface-container px-2 py-0.5 rounded-md">${escHtml(v.category_name)}</span>` : ''}
        </div>
        
        <div class="flex items-center gap-2 mt-3 pt-3 border-t border-surface-container-highest">
          <button class="flex-1 h-9 rounded-full bg-primary/10 text-primary font-label-sm flex items-center justify-center gap-1 hover:bg-primary hover:text-on-primary transition-colors watch-btn" data-id="${v.id}">
            <span class="material-symbols-outlined text-[16px]">play_arrow</span> Watch
          </button>
          <button class="flex-1 h-9 rounded-full border border-outline-variant text-on-surface-variant font-label-sm flex items-center justify-center gap-1 hover:bg-surface-container-high transition-colors share-lib-btn" data-id="${v.id}">
            <span class="material-symbols-outlined text-[16px]">share</span> Share
          </button>
        </div>
      </div>
    </div>`;
}

function renderPagination(container, total, skip, limit, cb) {
  container.innerHTML = '';
  if (total <= limit) return;
  const pages = Math.ceil(total / limit);
  const cur   = Math.floor(skip / limit);
  const el = document.createElement('div');
  el.className = 'flex items-center gap-2 bg-surface-container-lowest rounded-full border border-surface-container-highest p-1 shadow-sm';
  if (cur > 0) {
    const b = document.createElement('button');
    b.className = 'h-8 px-3 rounded-full text-primary hover:bg-primary/10 font-label-sm transition-colors flex items-center gap-1'; 
    b.innerHTML = '<span class="material-symbols-outlined text-[16px]">chevron_left</span> Prev';
    b.addEventListener('click', () => cb((cur - 1) * limit));
    el.appendChild(b);
  }
  const span = document.createElement('span');
  span.className = 'font-label-sm text-on-surface-variant px-2';
  span.textContent = `${cur + 1} / ${pages}`;
  el.appendChild(span);
  if (cur < pages - 1) {
    const b = document.createElement('button');
    b.className = 'h-8 px-3 rounded-full text-primary hover:bg-primary/10 font-label-sm transition-colors flex items-center gap-1';
    b.innerHTML = 'Next <span class="material-symbols-outlined text-[16px]">chevron_right</span>';
    b.addEventListener('click', () => cb((cur + 1) * limit));
    el.appendChild(b);
  }
  container.appendChild(el);
}
"""

content = re.sub(r"async function renderLibrary\(app\) \{.*?(?=\n/\* ══════════════════════════════════════════════════════════════════════════ \*/\n/\* PROGRESS)", library_code.strip() + "\n", content, flags=re.DOTALL)


with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(content)
