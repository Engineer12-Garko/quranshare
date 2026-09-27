import re

app_js_path = r"app\static\js\app.js"

with open(app_js_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix the v = res.video bug
# We replace:
#     const res = await API.get('/reminders/today');
#     const v = res.video;
# With:
#     const res = await API.get('/reminders/today');
#     const v = res; // the backend returns the video object directly

content = content.replace("const v = res.video;", "const v = res;")

with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(content)
