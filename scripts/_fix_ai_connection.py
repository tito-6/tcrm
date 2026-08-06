#!/usr/bin/env python3
from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
from tcrm.addons.tcrm_ai.services.crypto import decrypt_secret, normalize_api_key, encrypt_secret
from tcrm.addons.tcrm_ai.services.groq_provider import GroqProviderService
from tcrm.addons.tcrm_ai.services import entitlement as entitlement_svc
from tcrm.addons.tcrm_ai.services.constants import GROQ_BASE_URL

reg = Registry('tcrm_master')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    cfg = env['tcrm.ai.config'].sudo().get_config()
    print('before', 'conn', cfg.last_connection_status, 'err', cfg.last_safe_error, 'has', cfg.has_api_key)
    key = cfg._ensure_valid_groq_key()
    print('key_prefix', repr((key or '')[:8]), 'len', len(key or ''))
    if not key:
        # pull from provider again
        slot = env['tcrm.ai.key'].sudo().search([
            ('provider_id.provider_code', '=', 'groq'),
            ('active', '=', True),
        ], limit=1)
        key = normalize_api_key(slot.api_key) if slot else ''
        if key:
            cfg.sudo().write({'api_key_encrypted': encrypt_secret(env, key)})
            print('synced_from_provider', repr(key[:8]), len(key))

    models = [
        'llama-3.3-70b-versatile',
        'openai/gpt-oss-20b',
        'openai/gpt-oss-120b',
        'qwen/qwen3-32b',
    ]
    winner = None
    for model in models:
        try:
            svc = GroqProviderService(
                api_key=key,
                base_url=GROQ_BASE_URL,
                model=model,
                timeout=30,
                max_retries=0,
            )
            result = svc.test_connection()
            print('OK', model, result)
            winner = model
            break
        except Exception as exc:
            print('FAIL', model, type(exc).__name__, getattr(exc, 'safe_message', None) or exc,
                  getattr(exc, 'diagnostics', '')[:200])

    if winner and key:
        cfg.sudo().write({
            'model': winner,
            'ai_enabled': True,
            'allow_internet_research': True,
            'allow_payment_data': True,
            'allow_crm_data': True,
            'allow_sales_data': True,
            'allow_property_data': True,
            'allow_reports': True,
            'max_tool_calls': 16,
            'max_output_tokens': 4096,
            'last_connection_status': 'ok',
            'last_safe_error': False,
            'api_key_encrypted': encrypt_secret(env, key),
        })
        entitlement_svc.set_entitlement_state(env, 'active')
        print('restored model', winner, 'chat_block', entitlement_svc.chat_block_reason(env))
    else:
        print('NO_WORKING_MODEL')
    cr.commit()
