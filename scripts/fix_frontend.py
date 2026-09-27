import re

app_js_path = r"app\static\js\app.js"

with open(app_js_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Registration Form to add Gender
reg_patch = """
          <!-- Email Input -->
          <div class="relative">
            <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant">mail</span>
            <input type="email" id="reg-email" required placeholder="Email Address" class="w-full h-14 pl-12 pr-4 bg-surface-container-low border border-outline-variant rounded-xl font-body-lg text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all">
          </div>
          
          <!-- Gender Select -->
          <div class="relative">
            <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant">person</span>
            <select id="reg-gender" required class="w-full h-14 pl-12 pr-4 bg-surface-container-low border border-outline-variant rounded-xl font-body-lg text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all appearance-none cursor-pointer">
              <option value="" disabled selected>Select Gender</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select>
          </div>
"""

content = content.replace("""
          <!-- Email Input -->
          <div class="relative">
            <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant">mail</span>
            <input type="email" id="reg-email" required placeholder="Email Address" class="w-full h-14 pl-12 pr-4 bg-surface-container-low border border-outline-variant rounded-xl font-body-lg text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all">
          </div>
""", reg_patch)

# Update the submission payload for registration
content = content.replace(
    "const req = { full_name: fn, email, password: pw, phone: ph };",
    "const req = { full_name: fn, email, password: pw, phone: ph, gender: app.querySelector('#reg-gender').value };"
)

# 2. Add CSV Download Button in Admin
admin_patch = """
      <div class="card p-6 bg-surface-container rounded-[32px] border border-surface-container-highest shadow-sm">
        <div class="flex items-center justify-between mb-6">
          <div class="flex items-center gap-3">
            <div class="w-12 h-12 bg-primary-container rounded-2xl flex items-center justify-center">
              <span class="material-symbols-outlined text-on-primary-container text-[24px]">group</span>
            </div>
            <div>
              <h2 class="font-headline-sm text-on-surface m-0 leading-tight">Users</h2>
              <p class="font-body-sm text-on-surface-variant m-0">Manage registered users</p>
            </div>
          </div>
          <button class="h-10 px-4 bg-surface-container-high text-on-surface border border-outline-variant rounded-full font-label-md hover:bg-surface-dim transition-colors flex items-center gap-2" id="download-csv-btn">
            <span class="material-symbols-outlined text-[18px]">download</span> Export CSV
          </button>
        </div>
        
        <div id="admin-users-area" class="overflow-x-auto">
"""

content = content.replace("""
      <div class="card p-6 bg-surface-container rounded-[32px] border border-surface-container-highest shadow-sm">
        <div class="flex items-center gap-3 mb-6">
          <div class="w-12 h-12 bg-primary-container rounded-2xl flex items-center justify-center">
            <span class="material-symbols-outlined text-on-primary-container text-[24px]">group</span>
          </div>
          <div>
            <h2 class="font-headline-sm text-on-surface m-0 leading-tight">Users</h2>
            <p class="font-body-sm text-on-surface-variant m-0">Manage registered users</p>
          </div>
        </div>
        
        <div id="admin-users-area" class="overflow-x-auto">
""", admin_patch)

# Add event listener for CSV download
csv_listener = """
    app.querySelector('#download-csv-btn')?.addEventListener('click', async () => {
      const token = localStorage.getItem('token');
      if (!token) return;
      window.open(`/api/v1/admin/users/csv?token=${token}`, '_blank');
    });
    
    async function loadUsers() {
"""

content = content.replace("async function loadUsers() {", csv_listener)

# Fix API to allow token in query param for CSV download
# Wait, fast api route usually requires Bearer token, we need to pass the Bearer token as a query parameter for download, or use fetch and create object URL.
# Let's use fetch and blob:

csv_listener_fetch = """
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
"""

content = content.replace(csv_listener, csv_listener_fetch)

# Add Gender to the Admin User Table HTML
content = content.replace(
    "<th>Name</th><th>Email</th><th>Phone</th><th>Role</th><th>Actions</th>",
    "<th>Name</th><th>Email</th><th>Gender</th><th>Phone</th><th>Role</th><th>Actions</th>"
)
content = content.replace(
    "<td>${escHtml(u.email)}</td>\n            <td>${escHtml(u.phone || '-')}</td>",
    "<td>${escHtml(u.email)}</td>\n            <td class=\"capitalize\">${escHtml(u.gender || '-')}</td>\n            <td>${escHtml(u.phone || '-')}</td>"
)

with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(content)
