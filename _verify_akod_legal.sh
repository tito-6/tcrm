#!/bin/bash
set -euxo pipefail
for u in \
  https://akod.tech/tr/gizlilik-politikasi \
  https://akod.tech/tr/gizlilik-politikasi/ \
  https://akod.tech/tr/kvkk-aydinlatma-metni \
  https://akod.tech/tr/kvkk-aydinlatma-metni/
do
  code=$(curl -sS -o /tmp/akod_legal_check.html -w '%{http_code}|%{url_effective}' -L "$u")
  echo "$code"
done
echo '---titles---'
grep -oE '<title>[^<]+</title>' /tmp/akod_legal_check.html || true
grep -c 'Veri sorumlusu' /tmp/akod_legal_check.html || true
echo '---footer---'
curl -sS -L https://akod.tech/tr | grep -oE 'href="/tr/(gizlilik-politikasi|kvkk-aydinlatma-metni)"' | sort -u
echo '---nginx---'
grep -R "root \|try_files\|server_name\|akod" /etc/nginx/sites-enabled/ 2>/dev/null | head -50
