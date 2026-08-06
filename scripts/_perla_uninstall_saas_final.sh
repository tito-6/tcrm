#!/usr/bin/env bash
set -uo pipefail
export PYTHONPATH=/opt/tcrm/tcrm-src
export HOME=/var/lib/tcrm
CONF=/opt/tcrm/tcrm.prod.conf
PY=/opt/tcrm/venv/bin/python
LOG=/tmp/perla_uninstall_saas.log
: > "$LOG"

systemctl stop tcrm || true
pkill -f 'python -m tcrm' 2>/dev/null || true
sleep 1

# Ensure stub description exists
mkdir -p /opt/tcrm/custom_addons/tcrm_call_center/static/description
echo '<html><body>Santral</body></html>' > /opt/tcrm/custom_addons/tcrm_call_center/static/description/index.html
chown -R tcrm:tcrm /opt/tcrm/custom_addons/tcrm_call_center /opt/tcrm/custom_addons/tcrm_call_center_saas

echo "=== Mark perla modules ===" | tee -a "$LOG"
sudo -u tcrm env HOME=/var/lib/tcrm PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY' 2>&1 | tee -a "$LOG"
from tcrm.tools import config
config.parse_config(['-c','/opt/tcrm/tcrm.prod.conf','-d','perla_villalari'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
reg=Registry('perla_villalari')
with reg.cursor() as cr:
    env=Environment(cr, tcrm.SUPERUSER_ID, {})
    # Drop dependency
    cr.execute("""
        DELETE FROM ir_module_module_dependency d
         USING ir_module_module m
         WHERE d.module_id=m.id AND m.name='tcrm_call_center' AND d.name='tcrm_saas_core'
    """)
    print('dep_deleted', cr.rowcount)
    # Mark call_center to upgrade and saas_core to remove
    cr.execute("UPDATE ir_module_module SET state='to upgrade' WHERE name='tcrm_call_center' AND state='installed'")
    cr.execute("UPDATE ir_module_module SET state='to remove' WHERE name IN ('tcrm_saas_core','tcrm_call_center_saas') AND state IN ('installed','to upgrade')")
    cr.execute("SELECT name,state FROM ir_module_module WHERE name IN ('tcrm_saas_core','tcrm_call_center_saas','tcrm_call_center') ORDER BY name")
    for row in cr.fetchall():
        print('mark', row)
    cr.commit()
PY

echo "=== Apply module graph on perla via CLI ===" | tee -a "$LOG"
sudo -u tcrm env HOME=/var/lib/tcrm PYTHONPATH="$PYTHONPATH" "$PY" -m tcrm \
  -c "$CONF" -d perla_villalari -u tcrm_call_center --stop-after-init >>"$LOG" 2>&1
echo "CLI_RC=$?" | tee -a "$LOG"

echo "=== Verify perla ===" | tee -a "$LOG"
sudo -u tcrm env HOME=/var/lib/tcrm PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY' 2>&1 | tee -a "$LOG"
from tcrm.tools import config
config.parse_config(['-c','/opt/tcrm/tcrm.prod.conf','-d','perla_villalari'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
reg=Registry('perla_villalari')
with reg.cursor() as cr:
    env=Environment(cr, tcrm.SUPERUSER_ID, {})
    Mod=env['ir.module.module'].sudo()
    for name in ('tcrm_saas_core','tcrm_call_center_saas','tcrm_call_center'):
        m=Mod.search([('name','=',name)], limit=1)
        print(name, m.state if m else 'MISSING')
    print('tcrm.tenant', 'tcrm.tenant' in env)
    root=env.ref('tcrm_saas_core.menu_tcrm_root', raise_if_not_found=False)
    print('menu_tcrm_root', bool(root))
    print('santral', bool(env.ref('tcrm_call_center.menu_santral_root', raise_if_not_found=False)))
PY

# If still installed, force-hide menus as fallback
sudo -u tcrm env HOME=/var/lib/tcrm PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY' 2>&1 | tee -a "$LOG"
from tcrm.tools import config
config.parse_config(['-c','/opt/tcrm/tcrm.prod.conf','-d','perla_villalari'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
reg=Registry('perla_villalari')
with reg.cursor() as cr:
    env=Environment(cr, tcrm.SUPERUSER_ID, {})
    Mod=env['ir.module.module'].sudo()
    saas=Mod.search([('name','=','tcrm_saas_core')], limit=1)
    if saas and saas.state=='installed':
        print('FALLBACK hide menus')
        menus=env['ir.model.data'].sudo().search([('module','=','tcrm_saas_core'),('model','=','ir.ui.menu')])
        Menu=env['ir.ui.menu'].sudo()
        for md in menus:
            m=Menu.browse(md.res_id)
            if m.exists() and m.active:
                m.write({'active': False})
                print('hid', md.name)
        # also hide any root named TCRM Master
        for m in Menu.search([('name','ilike','TCRM Master'),('active','=',True)]):
            m.write({'active': False})
            print('hid_name', m.name)
        cr.commit()
    else:
        print('saas_core not installed — no fallback needed')
PY

echo "=== Master bridge install ===" | tee -a "$LOG"
sudo -u tcrm env HOME=/var/lib/tcrm PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY' 2>&1 | tee -a "$LOG"
from tcrm.tools import config
config.parse_config(['-c','/opt/tcrm/tcrm.prod.conf','-d','tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
reg=Registry('tcrm_master')
with reg.cursor() as cr:
    env=Environment(cr, tcrm.SUPERUSER_ID, {})
    Mod=env['ir.module.module'].sudo()
    Mod.update_list()
    cr.execute("UPDATE ir_module_module SET state='to upgrade' WHERE name='tcrm_call_center' AND state='installed'")
    cr.execute("UPDATE ir_module_module SET state='to install' WHERE name='tcrm_call_center_saas' AND state!='installed'")
    cr.commit()
PY
sudo -u tcrm env HOME=/var/lib/tcrm PYTHONPATH="$PYTHONPATH" "$PY" -m tcrm \
  -c "$CONF" -d tcrm_master -i tcrm_call_center_saas -u tcrm_call_center --stop-after-init >>"$LOG" 2>&1
echo "MASTER_CLI_RC=$?" | tee -a "$LOG"

sudo -u tcrm env HOME=/var/lib/tcrm PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY' 2>&1 | tee -a "$LOG"
from tcrm.tools import config
config.parse_config(['-c','/opt/tcrm/tcrm.prod.conf','-d','tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
reg=Registry('tcrm_master')
with reg.cursor() as cr:
    env=Environment(cr, tcrm.SUPERUSER_ID, {})
    Mod=env['ir.module.module'].sudo()
    for name in ('tcrm_saas_core','tcrm_call_center_saas','tcrm_call_center'):
        m=Mod.search([('name','=',name)], limit=1)
        print('master', name, m.state if m else 'MISSING')
PY

systemctl start tcrm
sleep 3
systemctl is-active tcrm | tee -a "$LOG"
echo DONE | tee -a "$LOG"
