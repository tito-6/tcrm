# -*- coding: utf-8 -*-
"""Hide CRM Organizasyon / Ekipler / Departmanlar / Personel menus."""


def migrate(cr, version):
    from tcrm import SUPERUSER_ID, api
    from tcrm.addons.tcrm_org.hooks import _hide_crm_org_menus

    env = api.Environment(cr, SUPERUSER_ID, {})
    _hide_crm_org_menus(env)
