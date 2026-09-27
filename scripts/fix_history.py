import re

with open('previous_app.js', encoding='utf-8') as f:
    prev = f.read()

# Extract HISTORY section
hist_match = re.search(r'(/\* ══════════════════════════════════════════════════════════════════════════ \*/\n/\* HISTORY.*?)(?=\n/\* ══════════════════════════════════════════════════════════════════════════ \*/\n/\* PROGRESS)', prev, re.DOTALL)
if hist_match:
    hist_code = hist_match.group(1)
    
    with open('app/static/js/app.js', encoding='utf-8') as f:
        curr = f.read()
        
    # Inject it back before PROGRESS
    curr = re.sub(r'(?=\n/\* ══════════════════════════════════════════════════════════════════════════ \*/\n/\* PROGRESS)', '\n\n' + hist_code + '\n\n', curr)
    
    with open('app/static/js/app.js', 'w', encoding='utf-8') as f:
        f.write(curr)
    print("History restored.")
else:
    print("Could not find History in previous_app.js")
