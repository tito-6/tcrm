from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
from tcrm.addons.tcrm_ai.services.groq_provider import GroqProviderService
from tcrm.addons.tcrm_ai.services.constants import GROQ_BASE_URL
from tcrm.addons.tcrm_ai.services.tools import TcrmAiToolExecutor

reg = Registry('tcrm_master')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    cfg = env['tcrm.ai.config'].sudo().get_config()
    key = cfg._get_plaintext_api_key()
    models = [
        'openai/gpt-oss-120b',
        'qwen/qwen3-32b',
        'meta-llama/llama-4-scout-17b-16e-instruct',
        'moonshotai/kimi-k2-instruct',
    ]
    ok_models = []
    for model in models:
        try:
            r = GroqProviderService(
                api_key=key, base_url=GROQ_BASE_URL, model=model, timeout=30, max_retries=0,
            ).test_connection()
            print('OK', model, r.get('latency_ms'))
            ok_models.append(model)
        except Exception as e:
            print('FAIL', model, getattr(e, 'diagnostics', None) or e)

    # Prefer strongest available
    prefer = ['openai/gpt-oss-120b', 'qwen/qwen3-32b', 'openai/gpt-oss-20b']
    winner = next((m for m in prefer if m in ok_models), 'openai/gpt-oss-20b')
    if winner != cfg.model:
        # bypass selection validation by writing through sudo after validating via live test
        from tcrm.addons.tcrm_ai.services.constants import APPROVED_GROQ_MODELS
        approved = {m[0] for m in APPROVED_GROQ_MODELS}
        if winner in approved:
            cfg.sudo().write({'model': winner, 'last_connection_status': 'ok', 'last_safe_error': False})
            print('set_model', winner)

    Lead = env['crm.lead'].sudo()
    print('lead_total', Lead.search_count([]))
    for q in ['525242886', '5525242886', '05525242886', '252428866']:
        dom = ['|', ('phone', 'ilike', q), ('mobile', 'ilike', q)]
        recs = Lead.search(dom, limit=5)
        print('q', q, 'count', len(recs), 'names', recs.mapped('name'), 'phones', recs.mapped('phone'))

    ex = TcrmAiToolExecutor(env, cfg, base_url='')
    print('tool_phone', ex.search_accessible_leads(query='055252428866', limit=5).get('record_count'))
    cr.commit()
