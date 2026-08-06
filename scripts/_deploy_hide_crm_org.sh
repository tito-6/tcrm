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
  echo "=== $db ==="
  has=$(sudo -u postgres psql -d "$db" -Atc "SELECT 1 FROM ir_module_module WHERE name='tcrm_org' AND state='installed' LIMIT 1" || true)
  if [[ "$has" != "1" ]]; then
    echo "skip (tcrm_org not installed)"
    continue
  fi
  sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" -m tcrm \
    -c "$CONF" -d "$db" -u tcrm_org --stop-after-init || echo "WARN upgrade $db"
  sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" - <<PY
from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', '$db'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
from tcrm.addons.tcrm_org.hooks import _hide_crm_org_menus
reg = Registry('$db')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    _hide_crm_org_menus(env)
    for xmlid in (
        'crm.sales_team_menu_team_pipeline',
        'tcrm_org.menu_tcrm_org_chart',
        'tcrm_org.menu_tcrm_org_departments',
        'tcrm_org.menu_tcrm_org_teams',
        'tcrm_org.menu_tcrm_org_users',
        'tcrm_org.menu_tcrm_org_access',
    ):
        m = env.ref(xmlid, raise_if_not_found=False)
        parent = m.parent_id.display_name if m and m.parent_id else None
        print(xmlid, 'active=', bool(m.active) if m else None, 'parent=', parent)
    cr.commit()
PY
done

systemctl start tcrm
sleep 2
systemctl is-active tcrm
echo DONE
