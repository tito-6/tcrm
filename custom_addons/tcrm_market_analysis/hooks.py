# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Assign admin group to settings users; optional company demo when flag set."""
    try:
        admin_group = env.ref("tcrm_market_analysis.group_market_admin")
        settings = env.ref("base.group_system")
        settings.write({"implied_ids": [(4, admin_group.id)]})
    except Exception:
        _logger.exception("market analysis post_init group link failed")

    # Local multi-company on tcrm_master needs an explicit opt-in to store listings.
    # Dedicated tenant databases do not need this parameter.
    try:
        ICP = env["ir.config_parameter"].sudo()
        if env.cr.dbname == "tcrm_master" and not ICP.get_param("tcrm_market_analysis.allow_master_listings"):
            ICP.set_param("tcrm_market_analysis.allow_master_listings", "1")
            _logger.warning(
                "tcrm_market_analysis.allow_master_listings=1 set for multi-company master. "
                "Clear this on production if tenants use dedicated databases."
            )
    except Exception:
        _logger.exception("market analysis master listing flag init failed")

    if env.context.get("tcrm_market_seed_demo") or env["ir.config_parameter"].sudo().get_param(
        "tcrm_market_analysis.auto_demo"
    ) == "1":
        from .services.demo_seed import seed_company_demo
        companies = env["res.company"].search([], order="id", limit=2)
        for idx, company in enumerate(companies):
            scenario = "istanbul" if idx == 0 else "ankara_izmir"
            try:
                seed_company_demo(
                    env(context=dict(env.context, tcrm_market_allow_master_company_seed=True)),
                    company,
                    scenario=scenario,
                )
            except Exception:
                _logger.exception("demo seed failed for company %s", company.id)
