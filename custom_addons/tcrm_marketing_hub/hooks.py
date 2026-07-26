# -*- coding: utf-8 -*-
import os


def post_init_hook(env):
    """Seed Zernio API key from env if not already configured."""
    ICP = env['ir.config_parameter'].sudo()
    if ICP.get_param('tcrm_marketing_hub.zernio_api_key'):
        return
    key = (os.environ.get('ZERNIO_API_KEY') or '').strip()
    if key:
        ICP.set_param('tcrm_marketing_hub.zernio_api_key', key)
    ICP.set_param(
        'tcrm_marketing_hub.zernio_base_url',
        ICP.get_param('tcrm_marketing_hub.zernio_base_url') or 'https://zernio.com/api/v1',
    )
