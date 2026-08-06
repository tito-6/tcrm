#!/usr/bin/env bash
set -euo pipefail
sed -i 's/\r$//' /opt/tcrm/scripts/_apply_ai_power_db.py || true
systemctl restart tcrm
sleep 5
for db in tcrm_master disposable_test perla_villalari; do
  echo "==== $db ===="
  sudo -u tcrm env PYTHONPATH=/opt/tcrm/tcrm-src /opt/tcrm/venv/bin/python \
    /opt/tcrm/scripts/_apply_ai_power_db.py "$db" || echo "FAIL $db"
done
systemctl is-active tcrm
echo DONE
