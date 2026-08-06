#!/usr/bin/env python3
import sys
from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', sys.argv[1]])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm

db = sys.argv[1]
reg = Registry(db)
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    from tcrm.tools import config as cfg
    control_db = cfg.get('tcrm_control_db') or 'tcrm_master'
    print('db=', db, 'control_db=', control_db, 'is_master=', db == control_db)
    env['ir.module.module']._tcrm_hide_apps_gallery_for_tenants()
    cr.commit()
    for xmlid in ('base.menu_management', 'base.menu_apps', 'base.menu_module_tree'):
        m = env.ref(xmlid, raise_if_not_found=False)
        print(xmlid, 'active=', bool(m.active) if m else None)
