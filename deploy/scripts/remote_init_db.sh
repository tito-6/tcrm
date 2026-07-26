#!/usr/bin/env bash
set -euo pipefail
sudo -u postgres psql -c "ALTER DATABASE tcrm_master OWNER TO tcrm;"
sudo -u postgres psql -d tcrm_master -c "ALTER SCHEMA public OWNER TO tcrm;"
sudo -u postgres psql -d tcrm_master -c "GRANT ALL ON SCHEMA public TO tcrm;"
cd /opt/tcrm
sudo -u tcrm env PYTHONPATH=/opt/tcrm/tcrm-src /opt/tcrm/venv/bin/python -m tcrm \
  -c /opt/tcrm/tcrm.prod.conf -d tcrm_master -i base --stop-after-init
echo BASE_OK
sudo -u tcrm env PYTHONPATH=/opt/tcrm/tcrm-src /opt/tcrm/venv/bin/python -m tcrm \
  -c /opt/tcrm/tcrm.prod.conf -d tcrm_master \
  -i web,mail,crm,calendar,project_todo,tcrm_propertio,tcrm_saas_core,tcrm_call_center \
  --stop-after-init
echo MODULES_OK
systemctl restart tcrm
sleep 3
systemctl --no-pager status tcrm | head -25
curl -sI http://127.0.0.1:8069/web/login | head -15
echo DONE
