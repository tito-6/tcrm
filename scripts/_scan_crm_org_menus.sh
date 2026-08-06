#!/usr/bin/env bash
set -euo pipefail
for db in tcrm_master perla_villalari; do
  echo "==== $db ===="
  sudo -u tcrm env PYTHONPATH=/opt/tcrm/tcrm-src /opt/tcrm/venv/bin/python /tmp/scan_crm_org_menus.py "$db" || true
done
