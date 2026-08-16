#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=/opt/tcrm/tcrm-src
export HOME=/opt/tcrm
PY=/opt/tcrm/venv/bin/python
CONF=/opt/tcrm/tcrm.prod.conf

echo "=== service status ==="
systemctl is-active tcrm || true

echo "=== module status perla ==="
sudo -u postgres psql -d perla_villalari -c \
  "SELECT name, state, latest_version FROM ir_module_module WHERE name IN ('tcrm_marketing_hub','tcrm_lead_report') ORDER BY name;"

echo "=== crons perla ==="
sudo -u postgres psql -d perla_villalari -c \
  "SELECT ic.cron_name, ic.active, ic.interval_number, ic.interval_type, im.model FROM ir_cron ic JOIN ir_model im ON im.id=ic.model_id WHERE im.model IN ('tcrm.marketing.meta.lead','tcrm.marketing.daily.metric') ORDER BY ic.cron_name;"

if ! sudo -u postgres psql -d perla_villalari -tAc "SELECT 1 FROM ir_module_module WHERE name='tcrm_lead_report' AND state='installed' LIMIT 1;" | grep -q 1; then
  echo "=== lead_report not installed, running upgrade ==="
  systemctl stop tcrm
  sleep 2
  sudo -u tcrm env PYTHONPATH=$PYTHONPATH HOME=$HOME $PY -m tcrm -c $CONF -d perla_villalari -u tcrm_marketing_hub --stop-after-init
  sudo -u tcrm env PYTHONPATH=$PYTHONPATH HOME=$HOME $PY -m tcrm -c $CONF -d perla_villalari -i tcrm_lead_report --stop-after-init || \
  sudo -u tcrm env PYTHONPATH=$PYTHONPATH HOME=$HOME $PY -m tcrm -c $CONF -d perla_villalari -u tcrm_lead_report --stop-after-init
  systemctl start tcrm
  sleep 5
fi

echo "=== final module status ==="
sudo -u postgres psql -d perla_villalari -c \
  "SELECT name, state, latest_version FROM ir_module_module WHERE name IN ('tcrm_marketing_hub','tcrm_lead_report') ORDER BY name;"

echo "=== health ==="
curl -s -o /dev/null -w "perla_login=%{http_code}\n" --max-time 20 https://perlavillalari.tcrm.online/web/login
