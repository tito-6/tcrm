#!/bin/bash
set -euo pipefail
export HOME=/opt/tcrm
export PYTHONPATH=/opt/tcrm/tcrm-src
cd /opt/tcrm

echo "=== Stopping tcrm ==="
systemctl stop tcrm
sleep 2

echo "=== Installing tcrm_offer on akod_prod ==="
sudo -u tcrm env HOME=/opt/tcrm PYTHONPATH=/opt/tcrm/tcrm-src \
  /opt/tcrm/venv/bin/python -m tcrm \
  -c /opt/tcrm/tcrm.prod.conf -d akod_prod -i tcrm_offer --stop-after-init \
  2>&1 | tee /tmp/tcrm_offer_install.log | tail -60

echo "=== Setting public base URL ==="
sudo -u postgres psql -d akod_prod <<'SQL'
INSERT INTO ir_config_parameter (key, value, create_uid, write_uid, create_date, write_date)
VALUES ('tcrm_offer.public_base_url', 'https://akod.tcrm.online', 1, 1, NOW(), NOW())
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, write_date = NOW();
SQL

echo "=== Module state ==="
sudo -u postgres psql -d akod_prod -tAc "SELECT name, state FROM ir_module_module WHERE name='tcrm_offer';"

echo "=== Starting tcrm ==="
systemctl start tcrm
sleep 4
systemctl is-active tcrm
echo DONE
