# -*- coding: utf-8 -*-
def migrate(cr, version):
    """Disable Tcrm.com OAuth login button on existing DBs."""
    cr.execute("""
        UPDATE auth_oauth_provider
           SET enabled = false
         WHERE enabled IS TRUE
           AND (
                name ILIKE '%%Tcrm.com%%'
             OR auth_endpoint ILIKE '%%accounts.tcrm.com%%'
             OR css_class ILIKE '%%o_tcrm_provider%%'
           )
    """)
