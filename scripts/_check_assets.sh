#!/usr/bin/env bash
echo "=== recent errors (assets / qweb / santral / traceback) ==="
grep -iE "QWeb|asset|scss|SassError|Traceback|ERROR|dialer|tcrm_call_center" /opt/tcrm/tcrm_data/tcrm.log | tail -30
echo "=== contact_name populated sample ==="
sudo -u postgres psql -d tcrm_master -Atc "SELECT id, coalesce(contact_name,'(null)') FROM tcrm_call_record ORDER BY id DESC LIMIT 5;"
echo "=== commission display_name ==="
sudo -u postgres psql -d tcrm_master -Atc "SELECT id, display_name FROM propertio_commission ORDER BY id LIMIT 5;" 2>&1 | head -6
echo "=== force backend assets compile ==="
curl -s -o /dev/null -w "web_login=%{http_code}\n" https://tcrm.online/web/login
