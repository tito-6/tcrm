# -*- coding: utf-8 -*-
"""Install hooks: create empty disabled Santral config for current company."""
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    Config = env['tcrm.call.provider.config'].sudo()
    for company in env['res.company'].search([]):
        existing = Config.search([('company_id', '=', company.id)], limit=1)
        if existing:
            continue
        Config.create({
            'company_id': company.id,
            'provider': 'twilio',
            'enabled': False,
        })
        _logger.info(
            "Santral: created empty disabled config for company %s (db=%s)",
            company.name, env.cr.dbname,
        )
