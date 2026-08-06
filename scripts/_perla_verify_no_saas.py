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
    print('tcrm.tenant', 'tcrm.tenant' in env)
    print('menu_tcrm_root', bool(env.ref(
        'tcrm_saas_core.menu_tcrm_root', raise_if_not_found=False
    )))
    print('santral_root', bool(env.ref(
        'tcrm_call_center.menu_santral_root', raise_if_not_found=False
    )))
