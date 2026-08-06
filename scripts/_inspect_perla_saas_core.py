from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'perla_villalari'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm

reg = Registry('perla_villalari')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    Mod = env['ir.module.module'].sudo()
    core = Mod.search([('name', '=', 'tcrm_saas_core')], limit=1)
    print('tcrm_saas_core', core.state, core.latest_version)
    dep = env['ir.module.module.dependency'].sudo().search([
        ('name', '=', 'tcrm_saas_core'),
        ('module_id.state', 'in', ('installed', 'to upgrade', 'to remove')),
    ])
    print('dependents:')
    for d in dep:
        print(' -', d.module_id.name, d.module_id.state)
    menus = env['ir.model.data'].sudo().search([
        ('module', '=', 'tcrm_saas_core'),
        ('model', '=', 'ir.ui.menu'),
    ])
    Menu = env['ir.ui.menu'].sudo()
    print('saas_core menus:')
    for md in menus:
        m = Menu.browse(md.res_id)
        if m.exists():
            print(' -', md.name, 'active=', m.active, 'name=', m.name)
