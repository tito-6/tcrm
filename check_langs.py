import sys
sys.path.insert(0, '/opt/tcrm/tcrm-src')
import tcrm
import tcrm.tools.config

tcrm.tools.config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
import tcrm.modules.registry as registry_module
import tcrm.api as api_module

tcrm.tools.config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
registry = registry_module.Registry('tcrm_master')
with registry.cursor() as cr:
    env = api_module.Environment(cr, tcrm.SUPERUSER_ID, {})
    langs = env['res.lang'].search([])
    print("Installed langs:", [(l.code, l.name, l.active) for l in langs])
    website = env['website'].search([], limit=1)
    print("Website langs:", website.language_ids.mapped('code'))
    
    # Ensure tr_TR is active and added to website
    tr_lang = env['res.lang'].search([('code', '=', 'tr_TR')], limit=1)
    if not tr_lang:
        print("tr_TR not found in res.lang, installing...")
        # Activate or install tr_TR
        env['res.lang']._create_lang('tr_TR')
        tr_lang = env['res.lang'].search([('code', '=', 'tr_TR')], limit=1)
    elif not tr_lang.active:
        tr_lang.active = True
        print("Activated tr_TR")

    if tr_lang and website and tr_lang not in website.language_ids:
        website.write({'language_ids': [(4, tr_lang.id)]})
        print("Added tr_TR to website.language_ids!")
        cr.commit()
    else:
        print("tr_TR already in website.language_ids")
