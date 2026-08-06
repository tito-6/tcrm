from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm

reg = Registry('tcrm_master')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    Mod = env['ir.module.module'].sudo()
    Mod.update_list()
    bridge = Mod.search([('name', '=', 'tcrm_call_center_saas')], limit=1)
    print('bridge', bridge.state if bridge else 'MISSING', bridge.id if bridge else None)
    if not bridge:
        raise SystemExit('bridge module not in list')
    if bridge.state != 'installed':
        # Avoid docutils description_html crash
        bridge.write({'description': 'Santral master bridge', 'application': False})
        bridge.button_install()
        # Use load without description_html path if possible
        try:
            env['base.module.upgrade'].upgrade_module()
        except Exception as e:
            print('upgrade_module_error', type(e).__name__, e)
            # Fallback: mark and rely on next start? try registry reload
            from tcrm.modules.registry import Registry as Reg
            Reg.new('tcrm_master', update_module=True)
        bridge.invalidate_recordset()
    print('bridge_after', bridge.state)
    print('santral_yonetimi', bool(env.ref(
        'tcrm_call_center_saas.menu_santral_yonetimi', raise_if_not_found=False
    )))
    cr.commit()
