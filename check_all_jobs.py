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
    jobs = env['hr.job'].with_context(active_test=False).search([])
    print("ALL JOBS IN DB (INCLUDING ARCHIVED):")
    for j in jobs:
        print(f"ID: {j.id} | Name: '{j.name}' | Active: {j.active} | Website Published: {getattr(j, 'website_published', None)}")
