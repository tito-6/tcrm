# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Tenant DB safety for market listing writes."""
from tcrm.exceptions import UserError

MASTER_DB_NAME = "tcrm_master"


def assert_listing_write_allowed(env):
    """Refuse writing listing data into the master control DB unless explicitly allowed.

    Production: collect only inside the active tenant database.
    Tests/local multi-company: set context tcrm_market_allow_master_company_ops
    or ir.config_parameter tcrm_market_analysis.allow_master_listings=1.
    """
    dbname = env.cr.dbname
    if dbname != MASTER_DB_NAME:
        return
    if env.context.get("tcrm_market_allow_master_company_ops"):
        return
    allow = env["ir.config_parameter"].sudo().get_param(
        "tcrm_market_analysis.allow_master_listings"
    )
    if allow == "1":
        return
    raise UserError(
        "Listing data must not be written into the master control database "
        "'%s'. Run collection on an explicit tenant database." % dbname
    )


def assert_job_db_binding(env, tenant_db_name):
    if tenant_db_name and tenant_db_name != env.cr.dbname:
        raise UserError(
            "Job targets database '%s' but current DB is '%s'."
            % (tenant_db_name, env.cr.dbname)
        )
