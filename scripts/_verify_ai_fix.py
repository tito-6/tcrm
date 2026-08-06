from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
from tcrm.addons.tcrm_ai.services.crypto import decrypt_secret, normalize_api_key
from tcrm.addons.tcrm_ai.services import entitlement as entitlement_svc

reg = Registry('tcrm_master')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    ver = env['ir.module.module'].search([('name', '=', 'tcrm_ai')], limit=1)
    print('version', ver.latest_version, 'state', ver.state)
    Config = env['tcrm.ai.config'].sudo()
    print('config_count_before', Config.search_count([]))
    cfg = Config.get_config()
    print('get_config', cfg.id, 'enabled', cfg.ai_enabled, 'conn', cfg.last_connection_status)
    print('config_count_after', Config.search_count([]))
    plain = normalize_api_key(
        decrypt_secret(env, cfg.api_key_encrypted) if cfg.api_key_encrypted else ''
    )
    print('key_prefix', repr(plain[:8]), 'len', len(plain), 'gsk', plain.startswith('gsk_'))
    if hasattr(cfg, '_ensure_valid_groq_key'):
        key = cfg._ensure_valid_groq_key()
        print('after_heal', repr((key or '')[:8]), len(key or ''))
    else:
        print('NO_HEAL_METHOD')
    try:
        res = cfg.action_test_connection()
        print('test_ok', res.get('params', {}).get('message'))
    except Exception as e:
        print('test_err', type(e).__name__, e)
    cfg.invalidate_recordset()
    print('conn_after', cfg.last_connection_status, 'err', cfg.last_safe_error)
    print('entitlement', entitlement_svc.get_entitlement_state(env))
    print('chat_block', entitlement_svc.chat_block_reason(env))
    st = cfg.get_public_status()
    print('chat_enabled', st.get('chat_enabled'), 'reason', st.get('chat_disabled_reason'))
    print('masked', st.get('api_key_masked'))
    cr.commit()
