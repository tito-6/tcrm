from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
from tcrm.addons.tcrm_ai.services import entitlement as entitlement_svc
from tcrm.addons.tcrm_ai.services.tools import TcrmAiToolExecutor

reg = Registry('tcrm_master')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    cfg = env['tcrm.ai.config'].sudo().get_config()
    cfg.sudo().write({
        'model': 'openai/gpt-oss-20b',
        'ai_enabled': True,
        'allow_crm_data': True,
        'allow_sales_data': True,
        'allow_property_data': True,
        'allow_payment_data': True,
        'allow_reports': True,
        'allow_internet_research': True,
        'daily_request_limit': 2000,
        'daily_token_limit': 2000000,
        'monthly_usage_limit': 20000000,
        'rpm_limit': 60,
        'max_tool_calls': 16,
        'max_output_tokens': 4096,
        'request_timeout': 90,
        'last_connection_status': 'ok',
        'last_safe_error': False,
    })
    entitlement_svc.set_entitlement_state(env, 'active')
    print('limits', cfg.daily_request_limit, cfg.rpm_limit, 'ent', entitlement_svc.get_entitlement_state(env))
    ex = TcrmAiToolExecutor(env, cfg, base_url='')
    w = ex.web_search(query='İstanbulda hava nasıl bugün', limit=3)
    print('weather', w.get('record_count'), w.get('abstract'), w.get('data_source'))
    engine = env['tcrm.ai.engine']
    res = engine._ask('İstanbulda hava nasıl bugün?')
    print('ask', (res.get('answer') or '')[:400])
    print('chat_block', entitlement_svc.chat_block_reason(env))
    cr.commit()
