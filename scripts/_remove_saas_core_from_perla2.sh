#!/usr/bin/env bash
set -euxo pipefail
export PYTHONPATH=/opt/tcrm/tcrm-src
CONF=/opt/tcrm/tcrm.prod.conf
PY=/opt/tcrm/venv/bin/python

systemctl stop tcrm || true

echo "=== update module list on master ==="
sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY'
from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
reg = Registry('tcrm_master')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    env['ir.module.module'].update_list()
    cr.commit()
    print('module_list_updated')
PY

echo "=== install bridge + upgrade call_center on master ==="
sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" -m tcrm \
  -c "$CONF" -d tcrm_master -i tcrm_call_center_saas -u tcrm_call_center --stop-after-init

echo "=== upgrade call_center on perla ==="
sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" -m tcrm \
  -c "$CONF" -d perla_villalari -u tcrm_call_center --stop-after-init

echo "=== uninstall saas_core (+ bridge) on perla ==="
sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY'
from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'perla_villalari'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm

reg = Registry('perla_villalari')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    Mod = env['ir.module.module'].sudo()
    # Ensure dependency row is gone
    cr.execute("""
        DELETE FROM ir_module_module_dependency d
         USING ir_module_module m
         WHERE d.module_id = m.id
           AND m.name = 'tcrm_call_center'
           AND d.name = 'tcrm_saas_core'
    """)
    for name in ('tcrm_call_center_saas', 'tcrm_saas_core'):
        mod = Mod.search([('name', '=', name)], limit=1)
        print('before', name, mod.state if mod else 'MISSING')
        if mod and mod.state == 'installed':
            mod.button_immediate_uninstall()
            mod.invalidate_recordset()
            print('after', name, mod.state)
    cr.commit()
PY

echo "=== verify perla ==="
sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY'
from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'perla_villalari'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
reg = Registry('perla_villalari')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    Mod = env['ir.module.module'].sudo()
    for name in ('tcrm_saas_core', 'tcrm_call_center_saas', 'tcrm_call_center'):
        m = Mod.search([('name', '=', name)], limit=1)
        print('perla', name, m.state if m else 'MISSING')
    print('has_tcrm_tenant', 'tcrm.tenant' in env)
    print('santral_root', bool(env.ref('tcrm_call_center.menu_santral_root', raise_if_not_found=False)))
PY

echo "=== verify master ==="
sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" - <<'PY'
from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
reg = Registry('tcrm_master')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    Mod = env['ir.module.module'].sudo()
    for name in ('tcrm_saas_core', 'tcrm_call_center_saas', 'tcrm_call_center'):
        m = Mod.search([('name', '=', name)], limit=1)
        print('master', name, m.state if m else 'MISSING')
    print('has_tcrm_tenant', 'tcrm.tenant' in env)
    print('master_menu', bool(env.ref('tcrm_saas_core.menu_tcrm_root', raise_if_not_found=False)))
    print('santral_yonetimi', bool(env.ref('tcrm_call_center_saas.menu_santral_yonetimi', raise_if_not_found=False)))
PY

systemctl start tcrm
sleep 3
systemctl is-active tcrm
echo DONE
