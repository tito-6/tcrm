#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=/opt/tcrm/tcrm-src
export HOME=/opt/tcrm
PY=/opt/tcrm/venv/bin/python
CONF=/opt/tcrm/tcrm.prod.conf

systemctl stop tcrm || true
sleep 2

echo "=== upgrade marketing hub perla ==="
sudo -u tcrm env PYTHONPATH=$PYTHONPATH HOME=$HOME $PY -m tcrm server -c $CONF -d perla_villalari -u tcrm_marketing_hub --stop-after-init

echo "=== install lead report perla ==="
sudo -u tcrm env PYTHONPATH=$PYTHONPATH HOME=$HOME $PY -m tcrm server -c $CONF -d perla_villalari -i tcrm_lead_report --stop-after-init

echo "=== upgrade marketing hub master ==="
sudo -u tcrm env PYTHONPATH=$PYTHONPATH HOME=$HOME $PY -m tcrm server -c $CONF -d tcrm_master -u tcrm_marketing_hub --stop-after-init || true

echo "=== install lead report master ==="
sudo -u tcrm env PYTHONPATH=$PYTHONPATH HOME=$HOME $PY -m tcrm server -c $CONF -d tcrm_master -i tcrm_lead_report --stop-after-init || true

systemctl start tcrm
sleep 6
systemctl is-active tcrm

sudo -u postgres psql -d perla_villalari -c "SELECT name, state, latest_version FROM ir_module_module WHERE name IN ('tcrm_marketing_hub','tcrm_lead_report') ORDER BY name;"

curl -s -o /dev/null -w "perla=%{http_code}\n" https://perlavillalari.tcrm.online/web/login
