# -*- coding: utf-8 -*-
"""Recompute Meta lead creatives from cached ads (fixes missing quote import)."""


def migrate(cr, version):
    from tcrm import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    MetaLead = env['tcrm.marketing.meta.lead'].sudo()
    leads = MetaLead.search([])
    if not leads:
        return
    # Local cache only — do not hit Zernio during migrate
    leads.with_context(marketing_skip_creative=True).action_refresh_creative_preview()
