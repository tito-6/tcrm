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
    jobs = env['hr.job'].search([])
    print("ALL JOBS IN DB:")
    for j in jobs:
        print(f"ID: {j.id} | Name: '{j.name}' | Published: {getattr(j, 'website_published', None)} | Active: {j.active}")
    
    # Process jobs:
    # 1. Look for Python Developer job
    python_job = None
    for j in jobs:
        if 'python' in j.name.lower() or 'developer' in j.name.lower():
            python_job = j
            break
            
    if not python_job:
        print("Python Developer job not found, creating one...")
        python_job = env['hr.job'].create({
            'name': 'Python Developer',
            'website_published': False,
            'is_published': False if hasattr(env['hr.job'], 'is_published') else False,
            'active': True,
        })
    else:
        # Keep python job open (active=True), but UNPUBLISHED (website_published=False)
        vals = {'active': True}
        if hasattr(python_job, 'website_published'):
            vals['website_published'] = False
        if hasattr(python_job, 'is_published'):
            vals['is_published'] = False
        python_job.write(vals)
        print(f"Updated Python Developer (ID: {python_job.id}) to UNPUBLISHED (yayında değil).")

    # 2. For all other jobs: archive/unpublish or delete them
    for j in jobs:
        if j.id != python_job.id:
            print(f"Archiving/Unpublishing job ID {j.id}: '{j.name}'")
            vals = {'active': False}
            if hasattr(j, 'website_published'):
                vals['website_published'] = False
            if hasattr(j, 'is_published'):
                vals['is_published'] = False
            j.write(vals)
            
    cr.commit()
    print("Jobs update committed successfully!")
