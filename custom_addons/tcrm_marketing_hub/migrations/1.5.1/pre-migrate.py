# -*- coding: utf-8 -*-
"""Deduplicate meta ads before unique(platform_ad_id) constraint."""


def migrate(cr, version):
    cr.execute("""
        DELETE FROM tcrm_marketing_meta_ad a
        USING tcrm_marketing_meta_ad b
        WHERE a.platform_ad_id = b.platform_ad_id
          AND a.id < b.id
    """)
