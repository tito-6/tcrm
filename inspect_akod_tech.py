import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open(r'd:\tcrm\akod_tech_page.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("HTML length:", len(html))

# Search for all script tags
scripts = re.findall(r'<script[\s\S]*?</script>', html, re.IGNORECASE)
print(f"Found {len(scripts)} scripts:")
for i, s in enumerate(scripts):
    print(f"\n--- Script {i+1} ---")
    print(s[:1000])

# Search for all action attributes or form targets
forms = re.findall(r'<form[\s\S]*?>', html, re.IGNORECASE)
print(f"\nFound {len(forms)} forms:")
for f in forms:
    print(f)

# Search for any endpoint / webhook / api URLs in html
urls = re.findall(r'https?://[^\s\"\'<>]+', html)
print(f"\nURLs found in page:")
for u in set(urls):
    if 'akod' in u or 'tcrm' in u or 'webhook' in u or 'api' in u:
        print("  ", u)
