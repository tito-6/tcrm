# -*- coding: utf-8 -*-
from tcrm.addons.tcrm_propertio.hooks import (
    _force_inventory_menu_label,
    _translate_master_data_labels,
)


def migrate(cr, version):
    from tcrm import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    _force_inventory_menu_label(env)
    _translate_master_data_labels(env)
