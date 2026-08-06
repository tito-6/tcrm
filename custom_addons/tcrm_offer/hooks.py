# -*- coding: utf-8 -*-
import secrets


def post_init_hook(env):
    """Rotate token pepper away from the placeholder if still default."""
    ICP = env['ir.config_parameter'].sudo()
    current = ICP.get_param('tcrm_offer.token_pepper', '')
    if not current or current == 'change-me-on-install':
        ICP.set_param('tcrm_offer.token_pepper', secrets.token_urlsafe(32))
    base = ICP.get_param('tcrm_offer.public_base_url')
    if not base:
        # Prefer current web base; ops can override for akod.tcrm.online
        ICP.set_param(
            'tcrm_offer.public_base_url',
            ICP.get_param('web.base.url', ''),
        )
    # Prefer TRY for company + existing offers
    if hasattr(env['res.company'], '_tcrm_ensure_try_currency'):
        env['res.company']._tcrm_ensure_try_currency()
    try_cur = env['tcrm.offer']._default_offer_currency()
    if try_cur:
        env['tcrm.offer'].sudo().search(
            [('currency_id', '!=', try_cur.id)]
        ).write({'currency_id': try_cur.id})
