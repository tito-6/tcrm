# -*- coding: utf-8 -*-
from tcrm.addons.tcrm_propertio.hooks import _force_inventory_menu_label


def migrate(cr, version):
    from tcrm import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    _force_inventory_menu_label(env)
