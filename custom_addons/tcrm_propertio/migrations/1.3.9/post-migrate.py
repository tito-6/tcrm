# -*- coding: utf-8 -*-
"""Apps sidebar order: CRM → Propertio → Santral → Marketing Hub → Takvim → Yapılacaklar."""


def migrate(cr, version):
    from tcrm import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        from tcrm.addons.tcrm_propertio.hooks import _force_apps_sidebar_order
        _force_apps_sidebar_order(env)
    except Exception:
        pass
