import tcrm
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm.tools.config as config
config.parse_config(['-c', r'd:\tcrm\tcrm.conf'])

for db in ['tcrm_master', 'akod_prod', 'tcrm_db', 'tcrm']:
    try:
        registry = Registry(db)
        with registry.cursor() as cr:
            env = Environment(cr, tcrm.SUPERUSER_ID, {})
            # Clear caches
            env.registry.clear_cache()
            env['ir.qweb'].clear_caches()
            print(f"Cleared all QWeb and ORM caches for DB: {db}")
    except Exception as e:
        print(f"Skipped {db}: {e}")
