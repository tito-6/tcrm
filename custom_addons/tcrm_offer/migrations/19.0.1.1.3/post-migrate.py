# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from tcrm import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    if hasattr(env['res.company'], '_tcrm_ensure_try_currency'):
        env['res.company']._tcrm_ensure_try_currency()
    try_cur = env['res.currency'].with_context(active_test=False).search(
        [('name', '=', 'TRY')], limit=1
    )
    if try_cur:
        if not try_cur.active:
            try_cur.active = True
        offers = env['tcrm.offer'].sudo().search([
            ('currency_id', '!=', try_cur.id),
        ])
        if offers:
            offers.write({'currency_id': try_cur.id})
            _logger.info('tcrm_offer: set TRY on %s offers', len(offers))
    _logger.info('tcrm_offer: TRY currency migration done')
