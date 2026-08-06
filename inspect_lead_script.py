import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open(r'd:\tcrm\akod_tech_page.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find script 11 full content
scripts = re.findall(r'<script[\s\S]*?</script>', html, re.IGNORECASE)
for s in scripts:
    if 'data-lead-form' in s or 'api/lead' in s or 'lead-form' in s:
        print("=== LEAD FORM SCRIPT ===")
        print(s)
