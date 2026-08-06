#!/usr/bin/env python3
"""Hide CRM Teams / Organizasyon menus on the given DB."""
import sys
from tcrm.tools import config

db = sys.argv[1]
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', db])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm

XMLIDS = (
    'crm.sales_team_menu_team_pipeline',
    'crm.crm_team_config',
    'crm.crm_team_member_config',
    'tcrm_org.menu_tcrm_org_chart',
    'tcrm_org.menu_tcrm_org_departments',
    'tcrm_org.menu_tcrm_org_teams',
    'tcrm_org.menu_tcrm_org_users',
)

reg = Registry(db)
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    Menu = env['ir.ui.menu'].sudo()
    crm_root = env.ref('crm.crm_menu_root', raise_if_not_found=False)

    # Hide known XML IDs
    for xmlid in XMLIDS:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu and menu.active:
            menu.write({'active': False})
            print(db, 'hid', xmlid)

    # Hide any CRM-subtree menu whose EN/TR name is Teams / Ekipler / Organizasyon...
    deny_names = {
        'teams', 'sales teams', 'ekipler', 'organizasyon',
        'organizasyon şeması', 'organizasyon semasi',
        'departmanlar', 'personel',
    }
    if crm_root:
        candidates = Menu.search([('id', 'child_of', crm_root.id)])
        for menu in candidates:
            name = (menu.name or '').strip().lower()
            if name in deny_names and menu.active:
                # Keep Erişim Yönetimi
                if 'erişim' in name or 'access' in name:
                    continue
                menu.write({'active': False})
                print(db, 'hid_by_name', menu.id, menu.complete_name)

    # Move access menu if present
    access = env.ref('tcrm_org.menu_tcrm_org_access', raise_if_not_found=False)
    config_menu = env.ref('crm.crm_menu_config', raise_if_not_found=False)
    if access and config_menu:
        access.write({'parent_id': config_menu.id, 'active': True, 'sequence': 90})
        print(db, 'access_parent', access.complete_name)

    # Verify remaining CRM org-ish menus
    if crm_root:
        left = Menu.search([
            ('id', 'child_of', crm_root.id),
            ('active', '=', True),
            '|', '|', '|', '|',
            ('name', 'ilike', 'Ekip'),
            ('name', 'ilike', 'Organizasyon'),
            ('name', 'ilike', 'Departman'),
            ('name', 'ilike', 'Personel'),
            ('name', 'ilike', 'Team'),
        ])
        for m in left:
            print(db, 'STILL', m.id, m.complete_name)
    cr.commit()
    print(db, 'DONE')
