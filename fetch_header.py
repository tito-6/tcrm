import urllib.request
import re

url = "http://127.0.0.1:8069/"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req).read().decode('utf-8')
    # Find navbar section
    nav_match = re.search(r'<header.*?</header>', html, re.DOTALL)
    if nav_match:
        print("HEADER HTML:")
        print(nav_match.group(0))
    else:
        print("Header not found, printing first 2000 chars:")
        print(html[:2000])
except Exception as e:
    print("Error:", e)
