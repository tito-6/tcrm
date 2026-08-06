# -*- coding: utf-8 -*-
"""Hide public shop/community menus, force contact→CRM, rename AKOD, strip homepage block."""


def migrate(cr, version):
    from tcrm import SUPERUSER_ID, api
    from tcrm.addons.tcrm_web_enhance.hooks import (
        _force_contactus_crm_lead,
        _hide_public_website_menus,
        _rename_company_to_akod,
        _reset_homepage_product_block,
    )

    env = api.Environment(cr, SUPERUSER_ID, {})
    _hide_public_website_menus(env)
    _force_contactus_crm_lead(env)
    _rename_company_to_akod(env)
    _reset_homepage_product_block(env)
