#!/usr/bin/env bash
set -uo pipefail
export PYTHONPATH=/opt/tcrm/tcrm-src
CONF=/opt/tcrm/tcrm.prod.conf
PY=/opt/tcrm/venv/bin/python
LOG=/tmp/remove_saas_steps.log
: > "$LOG"
log() { echo "$*" | tee -a "$LOG"; }

systemctl stop tcrm || true
pkill -f 'python -m tcrm' 2>/dev/null || true
sleep 2

run_py() {
  local db="$1"
  local code="$2"
  sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" -c "$code" >>"$LOG" 2>&1
}

log "STEP1 master: update list, upgrade call_center, install bridge"
sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY' >>"$LOG" 2>&1
from tcrm.tools import config
config.parse_config(['-c','/opt/tcrm/tcrm.prod.conf','-d','tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
reg = Registry('tcrm_master')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    Mod = env['ir.module.module'].sudo()
    Mod.update_list()
    cc = Mod.search([('name','=','tcrm_call_center')], limit=1)
    print('cc', cc.state, cc.latest_version)
    cc.button_upgrade()
    bridge = Mod.search([('name','=','tcrm_call_center_saas')], limit=1)
    print('bridge', bridge.state if bridge else 'MISSING')
    if bridge and bridge.state != 'installed':
        bridge.button_install()
    env['base.module.upgrade'].upgrade_module()
    cr.commit()
    cc.invalidate_recordset(); bridge.invalidate_recordset()
    print('cc_after', cc.state, cc.latest_version)
    print('bridge_after', bridge.state if bridge else 'MISSING')
PY
log "STEP1 exit:$?"

log "STEP2 perla: upgrade call_center, uninstall saas_core"
sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY' >>"$LOG" 2>&1
from tcrm.tools import config
config.parse_config(['-c','/opt/tcrm/tcrm.prod.conf','-d','perla_villalari'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
reg = Registry('perla_villalari')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    Mod = env['ir.module.module'].sudo()
    Mod.update_list()
    cr.execute("""
        DELETE FROM ir_module_module_dependency d
         USING ir_module_module m
         WHERE d.module_id=m.id AND m.name='tcrm_call_center' AND d.name='tcrm_saas_core'
    """)
    print('dep_deleted', cr.rowcount)
    cc = Mod.search([('name','=','tcrm_call_center')], limit=1)
    print('cc', cc.state, cc.latest_version)
    cc.button_upgrade()
    for name in ('tcrm_call_center_saas', 'tcrm_saas_core'):
        m = Mod.search([('name','=',name)], limit=1)
        print('mark_uninstall', name, m.state if m else 'MISSING')
        if m and m.state == 'installed':
            m.button_uninstall()
    env['base.module.upgrade'].upgrade_module()
    cr.commit()
    for name in ('tcrm_saas_core','tcrm_call_center_saas','tcrm_call_center'):
        m = Mod.search([('name','=',name)], limit=1)
        print('final', name, m.state if m else 'MISSING')
    print('tcrm.tenant', 'tcrm.tenant' in env)
    root = env.ref('tcrm_saas_core.menu_tcrm_root', raise_if_not_found=False)
    print('menu_tcrm_root_exists', bool(root))
PY
log "STEP2 exit:$?"

log "STEP3 verify master"
sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY' >>"$LOG" 2>&1
from tcrm.tools import config
config.parse_config(['-c','/opt/tcrm/tcrm.prod.conf','-d','tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
reg = Registry('tcrm_master')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    Mod = env['ir.module.module'].sudo()
    for name in ('tcrm_saas_core','tcrm_call_center_saas','tcrm_call_center'):
        m = Mod.search([('name','=',name)], limit=1)
        print(name, m.state if m else 'MISSING')
    print('tcrm.tenant', 'tcrm.tenant' in env)
    print('menu_tcrm_root', bool(env.ref('tcrm_saas_core.menu_tcrm_root', raise_if_not_found=False)))
    print('santral_yonetimi', bool(env.ref('tcrm_call_center_saas.menu_santral_yonetimi', raise_if_not_found=False)))
PY
log "STEP3 exit:$?"

systemctl start tcrm
sleep 3
systemctl is-active tcrm | tee -a "$LOG"
log DONE
cat "$LOG"
