#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=/opt/tcrm/tcrm-src
CONF=/opt/tcrm/tcrm.prod.conf
PY=/opt/tcrm/venv/bin/python

systemctl stop tcrm

mapfile -t DBS < <(sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY'
from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
reg = Registry('tcrm_master')
dbs = ['tcrm_master']
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    if 'tcrm.tenant' in env:
        for t in env['tcrm.tenant'].sudo().search([('db_name', '!=', False)]):
            name = (t.db_name or '').strip()
            if name and name not in dbs:
                dbs.append(name)
print('\n'.join(dbs))
PY
)

for db in "${DBS[@]}"; do
  echo "=== upgrade web_enhance on $db ==="
  sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" -m tcrm \
    -c "$CONF" -d "$db" -u tcrm_web_enhance --stop-after-init || echo "WARN $db"
  echo "=== hide menus on $db ==="
  sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" /opt/tcrm/scripts/_hide_crm_teams_all_dbs.py "$db" || echo "WARN hide $db"
done

# Also upgrade tcrm_org on master
sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" -m tcrm \
  -c "$CONF" -d tcrm_master -u tcrm_org --stop-after-init || true

systemctl start tcrm
sleep 2
systemctl is-active tcrm
echo DONE
