import sys
sys.path.insert(0, '/opt/tcrm/tcrm-src')
import tcrm
import tcrm.tools.config
import tcrm.modules.registry as registry_module
import tcrm.api as api_module

tcrm.tools.config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
registry = registry_module.Registry('tcrm_master')
with registry.cursor() as cr:
    env = api_module.Environment(cr, tcrm.SUPERUSER_ID, {})
    views = env['ir.ui.view'].search([('key', 'like', 'tcrm_web_enhance%')])
    if not views:
        views = env['ir.ui.view'].search([('name', 'like', 'Docs%')])
    for v in views:
        print("View:", v.id, v.name, v.key)
