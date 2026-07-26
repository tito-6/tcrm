#!/usr/bin/env bash
set -euo pipefail

# Place base SQL if missing
mkdir -p /opt/tcrm/tcrm-src/tcrm/addons/base/data
if [ ! -f /opt/tcrm/tcrm-src/tcrm/addons/base/data/base_data.sql ]; then
  echo "base_data.sql missing"
  exit 1
fi

chown -R tcrm:tcrm /opt/tcrm

# Restore dumped DB
systemctl stop tcrm || true
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='tcrm_master' AND pid <> pg_backend_pid();" || true
sudo -u postgres dropdb --if-exists tcrm_master
sudo -u postgres createdb -O tcrm tcrm_master
sudo -u postgres pg_restore -d tcrm_master --no-owner --role=tcrm /opt/tcrm_master.dump || true
# pg_restore returns 1 with warnings often; verify table exists
sudo -u postgres psql -d tcrm_master -c "SELECT count(*) FROM ir_module_module;" 

# Ensure web.base.url and proxy settings
sudo -u postgres psql -d tcrm_master -c "UPDATE ir_config_parameter SET value='https://tcrm.online' WHERE key='web.base.url';"
sudo -u postgres psql -d tcrm_master -c "INSERT INTO ir_config_parameter (key, value, create_uid, create_date, write_uid, write_date)
  SELECT 'web.base.url', 'https://tcrm.online', 1, NOW(), 1, NOW()
  WHERE NOT EXISTS (SELECT 1 FROM ir_config_parameter WHERE key='web.base.url');"

# Upgrade Santral module
cd /opt/tcrm
sudo -u tcrm env PYTHONPATH=/opt/tcrm/tcrm-src /opt/tcrm/venv/bin/python -m tcrm \
  -c /opt/tcrm/tcrm.prod.conf -d tcrm_master -u tcrm_call_center --stop-after-init

systemctl restart tcrm
sleep 4
systemctl --no-pager status tcrm | head -30
curl -sI -H 'Host: tcrm.online' http://127.0.0.1:8069/web/login | head -20
echo DONE
