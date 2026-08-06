#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=/opt/tcrm/tcrm-src
CONF=/opt/tcrm/tcrm.prod.conf
PY=/opt/tcrm/venv/bin/python
ADDONS=/opt/tcrm/custom_addons

systemctl stop tcrm

# Ensure bridge module is on disk
ls -la "$ADDONS/tcrm_call_center_saas/__manifest__.py"
ls -la "$ADDONS/tcrm_call_center_saas/views/santral_master_views.xml"

echo "=== Update module list + upgrade call_center on master ==="
sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" -m tcrm \
  -c "$CONF" -d tcrm_master -i tcrm_call_center_saas -u tcrm_call_center --stop-after-init

echo "=== Upgrade call_center on perla (drop saas_core dependency) ==="
sudo -u tcrm env PYTHONPATH="$PYTHONPATH" "$PY" -m tcrm \
  -c "$CONF" -d perla_villalari -u tcrm_call_center --stop-after-init

echo "=== Uninstall tcrm_saas_core from perla ==="
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
    # Drop any leftover bridge if auto-installed
    for name in ('tcrm_call_center_saas', 'tcrm_saas_core'):
        mod = Mod.search([('name', '=', name), ('state', '=', 'installed')], limit=1)
        if not mod:
            print(name, 'not installed')
            continue
        print('uninstalling', name)
        # Use sudo path; tenant UI blocks are skipped for superuser in our patch
        # Prefer button_immediate_uninstall which commits internally — use mark + upgrade
        mod.button_immediate_uninstall()
        print(name, 'state_after', mod.state)
    cr.commit()
PY

# If button_immediate_uninstall restarted things oddly, ensure service stopped then verify
systemctl stop tcrm || true

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
        print(name, m.state if m else 'MISSING')
    # Master menus should be gone
    menus = env['ir.model.data'].sudo().search([
        ('module', '=', 'tcrm_saas_core'),
        ('model', '=', 'ir.ui.menu'),
    ])
    print('remaining_saas_menu_xmlids', len(menus))
    # Santral still present
    print('santral_menu', bool(env.ref('tcrm_call_center.menu_santral_root', raise_if_not_found=False)))
PY

echo "=== Verify master still has saas_core + bridge ==="
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
        print(name, m.state if m else 'MISSING')
    print('santral_yonetimi', bool(env.ref('tcrm_call_center_saas.menu_santral_yonetimi', raise_if_not_found=False) or env.ref('tcrm_call_center.menu_santral_yonetimi', raise_if_not_found=False)))
PY

systemctl start tcrm
sleep 3
systemctl is-active tcrm
echo DONE
