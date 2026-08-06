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
    
    for j in jobs:
        if j.id == 2:
            j.write({
                'name': 'Python Developer',
                'active': False,
                'website_published': False,
            })
            print(f"Job ID 2 updated to 'Python Developer', active=False, website_published=False.")
        else:
            j.write({
                'active': False,
                'website_published': False,
            })
            print(f"Job ID {j.id} ('{j.name}') archived/unpublished.")

    cr.commit()
    print("Jobs final fix committed successfully!")
