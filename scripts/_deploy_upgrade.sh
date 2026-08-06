#!/usr/bin/env bash
set -uo pipefail
export PYTHONPATH=/opt/tcrm/tcrm-src
cd /opt/tcrm
chown -R tcrm:tcrm /opt/tcrm/custom_addons/tcrm_web_enhance /opt/tcrm/custom_addons/tcrm_call_center /opt/tcrm/custom_addons/tcrm_saas_core /opt/tcrm/scripts 2>/dev/null || true

MODULES="${1:-tcrm_web_enhance,tcrm_call_center}"
DBS="${2:-tcrm_master}"

echo "=== stopping service ==="
systemctl stop tcrm
sleep 2

RC=0
for DB in $(echo "$DBS" | tr ',' ' '); do
  echo "=== upgrading $MODULES on $DB ==="
  sudo -u tcrm env PYTHONPATH=/opt/tcrm/tcrm-src /opt/tcrm/venv/bin/python -m tcrm \
    -c /opt/tcrm/tcrm.prod.conf -d "$DB" -u "$MODULES" --stop-after-init 2>&1 | tail -50
  this_rc=${PIPESTATUS[0]}
  if [ "$this_rc" -ne 0 ]; then RC=$this_rc; fi

  echo "=== strip youtube embeds on $DB ==="
  sudo -u tcrm env PYTHONPATH=/opt/tcrm/tcrm-src /opt/tcrm/venv/bin/python \
    /opt/tcrm/scripts/remove_youtube_videos.py -c /opt/tcrm/tcrm.prod.conf -d "$DB" 2>&1 | tail -30
done

echo "=== starting service ==="
systemctl start tcrm
sleep 5
systemctl is-active tcrm
echo "=== docs + login checks ==="
curl -s -o /dev/null -w "docs=%{http_code}\n" http://127.0.0.1:8069/docs
curl -s -o /dev/null -w "login=%{http_code}\n" http://127.0.0.1:8069/web/login
echo "upgrade_rc=$RC"
exit $RC
