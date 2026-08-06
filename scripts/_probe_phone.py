from tcrm.tools import config
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', 'tcrm_master'])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
from tcrm.addons.tcrm_ai.services.tools import TcrmAiToolExecutor
from tcrm.addons.tcrm_ai.services import entitlement as entitlement_svc

reg = Registry('tcrm_master')
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    cfg = env['tcrm.ai.config'].sudo().get_config()
    Lead = env['crm.lead']
    print('lead_fields_phone', [f for f in ('phone', 'mobile', 'phone_sanitized', 'partner_phone') if f in Lead._fields])
    Partner = env['res.partner']
    print('partner_phone_fields', [f for f in ('phone', 'mobile', 'phone_sanitized') if f in Partner._fields])
    # raw SQL digit search
    cr.execute("""
        SELECT id, name, phone
        FROM crm_lead
        WHERE regexp_replace(COALESCE(phone,''), '[^0-9]', '', 'g') LIKE '%525242886%'
           OR regexp_replace(COALESCE(phone,''), '[^0-9]', '', 'g') LIKE '%5525242886%'
        LIMIT 10
    """)
    rows = cr.fetchall()
    print('sql_leads', rows)
    cr.execute("""
        SELECT id, name, phone
        FROM res_partner
        WHERE regexp_replace(COALESCE(phone,''), '[^0-9]', '', 'g') LIKE '%525242886%'
           OR regexp_replace(COALESCE(phone,''), '[^0-9]', '', 'g') LIKE '%5525242886%'
        LIMIT 10
    """)
    print('sql_partners', cr.fetchall())
    ex = TcrmAiToolExecutor(env, cfg, base_url='')
    for q in ('055252428866', '05525242886', '5525242886', '525242886'):
        res = ex.search_accessible_leads(query=q, limit=5)
        print('tool', q, res.get('record_count'), [r.get('name') for r in res.get('rows', [])])
    print('status', cfg.model, cfg.last_connection_status, entitlement_svc.chat_block_reason(env))
