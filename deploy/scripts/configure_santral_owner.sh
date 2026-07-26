#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=/opt/tcrm/tcrm-src
cd /opt/tcrm
/opt/tcrm/venv/bin/python - <<'PY'
import os
from tcrm.tools import config as tcrm_config
tcrm_config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
from tcrm.orm.utils import SUPERUSER_ID

ACCOUNT_SID = os.environ['SANTRAL_ACCOUNT_SID']
API_KEY_SID = os.environ['SANTRAL_API_KEY_SID']
API_KEY_SECRET = os.environ['SANTRAL_API_KEY_SECRET']
AUTH_TOKEN = os.environ['SANTRAL_AUTH_TOKEN']
TWIML_APP_SID = os.environ.get('SANTRAL_TWIML_APP_SID', '')
CALLER_ID = os.environ.get('SANTRAL_CALLER_ID', '')
BASE_URL = os.environ.get('SANTRAL_CALLBACK_BASE', 'https://tcrm.online')

registry = Registry('tcrm_master')
with registry.cursor() as cr:
    env = Environment(cr, SUPERUSER_ID, {})
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
    if TWIML_APP_SID and CALLER_ID:
        vals['enabled'] = True
    config.write(vals)
    # Grant admin santral groups
    admin = env.ref('base.user_admin')
    admin.write({'group_ids': [(4, env.ref('tcrm_call_center.group_santral_admin').id),
                               (4, env.ref('tcrm_call_center.group_santral_recording_listen').id),
                               (4, env.ref('tcrm_call_center.group_santral_recording_download').id)]})
    cr.commit()
    print('company=', company.name)
    print('enabled=', config.enabled, 'configured=', config.is_configured)
    print('has_secret=', bool(config.api_key_secret_encrypted), 'has_token=', bool(config.auth_token_encrypted))
PY
