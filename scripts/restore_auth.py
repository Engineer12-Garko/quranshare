import re

with open('app_old.js', encoding='utf-16') as f:
    old_content = f.read()

# Extract missing auth functions
match = re.search(r'(/\* ══════════════════════════════════════════════════════════════════════════ \*/\n/\* LANDING.*?)(?=/\* ── Core share helper)', old_content, flags=re.DOTALL)
if match:
    missing_code = match.group(1)
    
    with open(r'app\static\js\app.js', encoding='utf-8') as f:
        new_content = f.read()
        
    new_content = new_content.replace('/* ── Core share helper', missing_code + '\n/* ── Core share helper')
    
    with open(r'app\static\js\app.js', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Restored auth functions successfully.")
else:
    print("Could not find the auth functions in app_old.js.")
