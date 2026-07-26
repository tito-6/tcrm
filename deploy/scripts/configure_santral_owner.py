#!/usr/bin/env python3
"""One-time owner-tenant Santral config writer. Do not commit secrets into Git."""
import os
import sys

sys.path.insert(0, '/opt/tcrm/tcrm-src')
os.environ.setdefault('PYTHONPATH', '/opt/tcrm/tcrm-src')

import tcrm
from tcrm import SUPERUSER_ID as SID
from tcrm.tools import config as tcrm_config
from tcrm.modules.registry import Registry
from tcrm.api import Environment

CONF = '/opt/tcrm/tcrm.prod.conf'
tcrm_config.parse_config(['-c', CONF])

# Read secrets from env — never hardcode in repo files that get committed.
ACCOUNT_SID = os.environ.get('SANTRAL_ACCOUNT_SID', '')
API_KEY_SID = os.environ.get('SANTRAL_API_KEY_SID', '')
API_KEY_SECRET = os.environ.get('SANTRAL_API_KEY_SECRET', '')
AUTH_TOKEN = os.environ.get('SANTRAL_AUTH_TOKEN', '')
TWIML_APP_SID = os.environ.get('SANTRAL_TWIML_APP_SID', '')
CALLER_ID = os.environ.get('SANTRAL_CALLER_ID', '')
BASE_URL = os.environ.get('SANTRAL_CALLBACK_BASE', 'https://tcrm.online')

if not all([ACCOUNT_SID, API_KEY_SID, API_KEY_SECRET, AUTH_TOKEN]):
    print('Missing SANTRAL_* env vars')
    sys.exit(2)

registry = Registry('tcrm_master')
with registry.cursor() as cr:
    env = Environment(cr, SID, {})
    company = env['res.company'].sudo().search([], limit=1)
    Config = env['tcrm.call.provider.config'].sudo()
    config = Config.search([('company_id', '=', company.id)], limit=1)
    if not config:
        config = Config.create({'company_id': company.id, 'provider': 'twilio'})
    vals = {
        'account_sid': ACCOUNT_SID,
        'api_key_sid': API_KEY_SID,
        'api_key_secret': API_KEY_SECRET,
        'auth_token': AUTH_TOKEN,
        'public_callback_base_url': BASE_URL,
        'recording_enabled': True,
        'dual_channel_recording': True,
        'recording_announcement_enabled': True,
    }
    if TWIML_APP_SID:
        vals['twiml_app_sid'] = TWIML_APP_SID
    if CALLER_ID:
        vals['verified_caller_id'] = CALLER_ID
    # Enable only when fully configured
    if TWIML_APP_SID and CALLER_ID:
        vals['enabled'] = True
    config.write(vals)
    cr.commit()
    print('Santral config written for company', company.name, 'enabled=', config.enabled, 'configured=', config.is_configured)
