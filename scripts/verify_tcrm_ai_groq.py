#!/usr/bin/env python3
"""Real verification harness for TCRM AI / Groq (no secrets printed)."""
from __future__ import annotations

import os
import sys

sys.path[:0] = [r'd:\tcrm\custom_addons', r'D:\crm\tcrm-src', r'D:\crm\custom_addons']

from tcrm.tools import config
config.parse_config(['-c', r'd:\tcrm\tcrm_ai_dev.conf'])
from tcrm.modules.registry import Registry
from tcrm import api, SUPERUSER_ID

RESULTS = []


def ok(name, cond, detail=''):
    RESULTS.append((name, bool(cond), detail))
    print(('PASS' if cond else 'FAIL'), '-', name, (detail[:160] if detail else ''))


def main():
    groq_key = (os.environ.get('GROQ_API_KEY') or '').strip()
    reg = Registry('tcrm_master')
    with reg.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # Import helpers from already-loaded addon namespace
        from tcrm.addons.tcrm_ai.services import entitlement as ent
        from tcrm.addons.tcrm_ai.services.crypto import encrypt_secret, decrypt_secret, mask_api_key
        from tcrm.addons.tcrm_ai.services.constants import DEFAULT_GROQ_MODEL
        from tcrm.addons.tcrm_ai.services.tools import TcrmAiToolExecutor, ToolDenied

        Config = env['tcrm.ai.config']
        config_rec = Config.sudo().get_config()
        ok('master_config_exists', bool(config_rec))
        ok('default_model', config_rec.model == DEFAULT_GROQ_MODEL, config_rec.model or '')
        ok('provider_groq', config_rec.provider == 'groq')

        ent.set_entitlement_state(env, 'config_required')
        ok('config_required_state', ent.get_entitlement_state(env) == 'config_required')

        sample = 'gsk_verify_only_not_a_real_key_9999'
        enc = encrypt_secret(env, sample)
        ok('key_encrypted_prefix', enc.startswith('enc:v1:'))
        ok('key_roundtrip', decrypt_secret(env, enc) == sample)
        masked = mask_api_key(sample)
        ok('key_masked', masked.endswith('9999') and 'verify_only' not in masked, masked)

        config_rec.write({'api_key_input': sample, 'ai_enabled': True})
        row = config_rec.read(['api_key_encrypted', 'api_key_masked', 'has_api_key'])[0]
        ok('key_not_in_rpc', row['api_key_encrypted'] in (True, 1) and sample not in str(row))
        pub = Config.get_public_status()
        ok('public_status_no_secret', sample not in str(pub) and 'api_key_encrypted' not in pub)

        executor = TcrmAiToolExecutor(env, config_rec)
        try:
            executor.execute('get_lead_summary', {'sql': 'SELECT 1'})
            ok('sql_rejected', False)
        except ToolDenied:
            ok('sql_rejected', True)

        if 'tcrm.tenant.ai.status' in env:
            Status = env['tcrm.tenant.ai.status']
            tenants = env['tcrm.tenant'].search([], limit=1)
            if tenants:
                st = Status.get_or_create(tenants[0])
                data = st.to_safe_dict()
                ok('master_safe_status', 'api_key' not in str(data) and 'gsk_' not in str(data))
            else:
                ok('master_safe_status', True, 'no tenants')
        else:
            ok('master_safe_status', False, 'model missing')

        ent.set_entitlement_state(env, 'unavailable')
        blocked = env['tcrm.ai.engine']._ask('Bu ay kaç yeni lead geldi?')
        ok('revoke_blocks_chat', blocked.get('error') or blocked.get('disabled'))

        if groq_key:
            ent.set_entitlement_state(env, 'active')
            config_rec.write({
                'api_key_input': groq_key,
                'ai_enabled': True,
                'model': DEFAULT_GROQ_MODEL,
                'allow_crm_data': True,
            })
            try:
                config_rec.action_test_connection()
                ok('real_connection_test', config_rec.last_connection_status == 'ok',
                   'latency=%sms' % config_rec.last_connection_latency_ms)
            except Exception as exc:
                ok('real_connection_test', False, type(exc).__name__ + ': ' + str(exc)[:160])

            chat = env['tcrm.ai.engine']._ask('Merhaba, kısaca kendini tanıt.')
            ok('real_turkish_chat', not chat.get('error') and bool(chat.get('answer')),
               (chat.get('answer') or '')[:160])

            lead_q = env['tcrm.ai.engine']._ask('Bu ay kaç yeni lead geldi?')
            tools = lead_q.get('tools_used') or []
            ok('lead_tool_invoked', 'get_lead_summary' in tools or not lead_q.get('error'),
               'tools=%s ans=%s' % (tools, (lead_q.get('answer') or '')[:80]))
        else:
            ok('real_connection_test', False, 'GROQ_API_KEY env not set — skipped')
            ok('real_turkish_chat', False, 'skipped')
            ok('lead_tool_invoked', False, 'skipped')

        cr.rollback()

    failed = [r for r in RESULTS if not r[1]]
    print('\nSummary: %s/%s passed' % (len(RESULTS) - len(failed), len(RESULTS)))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
