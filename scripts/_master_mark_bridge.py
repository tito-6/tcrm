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
    cr.execute(
        "UPDATE ir_module_module SET state='to install' "
        "WHERE name='tcrm_call_center_saas' AND state <> 'installed'"
    )
    cr.execute(
        "UPDATE ir_module_module SET state='to upgrade' "
        "WHERE name='tcrm_call_center' AND state='installed'"
    )
    cr.execute(
        "SELECT name, state FROM ir_module_module "
        "WHERE name IN ('tcrm_call_center_saas', 'tcrm_call_center') ORDER BY name"
    )
    print('before', cr.fetchall())
    cr.commit()
