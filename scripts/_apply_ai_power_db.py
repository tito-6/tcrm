#!/usr/bin/env python3
"""Apply expanded TCRM AI access on a single DB (arg1)."""
import sys

from tcrm.tools import config

db = sys.argv[1]
config.parse_config(['-c', '/opt/tcrm/tcrm.prod.conf', '-d', db])
from tcrm.modules.registry import Registry
from tcrm.api import Environment
import tcrm
from tcrm.addons.tcrm_ai.services.constants import DEFAULT_GROQ_MODEL
from tcrm.addons.tcrm_ai.services.tools import TcrmAiToolExecutor
from tcrm.addons.tcrm_ai.services import entitlement as entitlement_svc

reg = Registry(db)
with reg.cursor() as cr:
    env = Environment(cr, tcrm.SUPERUSER_ID, {})
    if 'tcrm.ai.config' not in env:
        print(db, 'NO_AI_MODULE')
        raise SystemExit(0)
    cfg = env['tcrm.ai.config'].sudo().get_config()
    vals = {
        'allow_crm_data': True,
        'allow_sales_data': True,
        'allow_property_data': True,
        'allow_payment_data': True,
        'allow_reports': True,
        'allow_internet_research': True,
        'max_tool_calls': 16,
        'max_output_tokens': 4096,
        'request_timeout': 90,
        'daily_request_limit': 500,
        'daily_token_limit': 500000,
        'rpm_limit': 30,
        'model': DEFAULT_GROQ_MODEL,
        'ai_enabled': True,
    }
    # Keep existing working key/connection if present
    cfg.write(vals)
    if cfg.has_api_key and cfg.last_connection_status != 'ok':
        try:
            cfg._ensure_valid_groq_key()
            cfg.action_test_connection()
        except Exception as exc:
            print(db, 'test_warn', type(exc).__name__, exc)
    print(
        db,
        'model', cfg.model,
        'internet', cfg.allow_internet_research,
        'payment', cfg.allow_payment_data,
        'conn', cfg.last_connection_status,
        'chat_block', entitlement_svc.chat_block_reason(env),
    )
    ex = TcrmAiToolExecutor(env, cfg, base_url='')
    print(db, 'tools', len(ex.available_tool_defs()))
    for q in ('055252428866', '5525242886', '05525242886'):
        try:
            res = ex.search_accessible_leads(query=q, limit=5)
            print(db, 'phone', q, 'count', res.get('record_count'),
                  [r.get('name') for r in res.get('rows', [])][:3])
        except Exception as e:
            print(db, 'phone_err', q, type(e).__name__, e)
    # Hide apps on tenants
    if 'ir.module.module' in env and hasattr(env['ir.module.module'], '_tcrm_hide_apps_gallery_for_tenants'):
        env['ir.module.module']._tcrm_hide_apps_gallery_for_tenants()
        for xmlid in ('base.menu_management', 'base.menu_apps', 'base.menu_module_tree'):
            m = env.ref(xmlid, raise_if_not_found=False)
            print(db, xmlid, 'active', bool(m.active) if m else None)
    cr.commit()
