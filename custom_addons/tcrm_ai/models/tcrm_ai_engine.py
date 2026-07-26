# Part of TCRM AI. See LICENSE for details.

import json
import logging
import re
from urllib.parse import quote

from tcrm import models

from ..utils import conversation_memory
from ..utils import context_resolver
from ..utils import prompt_builder
from ..utils import tool_executor
from ..utils import fallback_handler
from ..utils import response_formatter
from ..utils.api_manager import TCRMApiManager
from ..utils.api_manager import AllProvidersExhaustedError
from ..utils.api_manager.adapters import get_adapter

_logger = logging.getLogger(__name__)


class TcrmAiEngine(models.AbstractModel):
    _name = 'tcrm.ai.engine'
    _description = 'TCRM AI Engine'

    def _has_provider_keys(self, env):
        """True if at least one active provider has at least one active key."""
        return bool(
            env['tcrm.ai.key'].sudo().search_count([
                ('active', '=', True),
                ('provider_id.active', '=', True),
            ])
        )

    def _get_account_context(self, max_models=40, max_partners=500):
        """Build a short knowledge summary of the account DB for the AI (counts, key models). Kept small to save tokens."""
        env = self.env
        lines = []
        try:
            if 'res.partner' in env:
                n = env['res.partner'].search_count([])
                lines.append("Partners/contacts: %d" % min(n, max_partners) + (" (showing cap %d)" % max_partners if n > max_partners else ""))
            for model_name in ('sale.order', 'crm.lead', 'project.project', 'account.move', 'propertio.sale', 'crm.property.sale'):
                if model_name in env:
                    try:
                        n = env[model_name].search_count([])
                        lines.append("%s: %d records" % (model_name, n))
                    except Exception:
                        pass
            if lines:
                return "Account summary (use for quick answers; use tools for details): " + "; ".join(lines) + "."
        except Exception as e:
            _logger.warning("TCRM AI account context: %s", e)
        return ""

    def _ask(self, message, base_url=None):
        """
        Run TCRM AI on the given message. Uses current env (master or tenant DB).
        Returns dict: answer, tables (list of {headers, rows}), links (list of {url, label}), error (bool).
        """
        env = self.env
        if base_url is None:
            base_url = env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069').rstrip('/')
        db_name = env.cr.dbname
        # Ensure tcrm_ai_key table and config columns exist before querying providers/keys
        config = env['tcrm.ai.config'].sudo().get_config()
        has_keys = self._has_provider_keys(env)
        gen_max_tokens = max(256, min(8192, config.max_tokens or 4096))
        gen_temperature = max(0.0, min(1.0, config.temperature if config.temperature is not None else 0.7))
        gen_timeout = max(5, min(120, config.request_timeout or 45))

        api_key = ''
        model_name = 'gemini-3-flash-preview'
        models_to_try = [model_name]

        if not has_keys:
            try:
                from tcrm_ai.models.tcrm_ai_config import (
                    FALLBACK_ORDER,
                    DEPRECATED_GEMINI_TO_CURRENT,
                )
                config = env['tcrm.ai.config'].sudo().get_config()
                api_key = (config.gemini_api_key or '').strip()
                model_name = config.gemini_model or 'gemini-2.0-flash'
                model_name = DEPRECATED_GEMINI_TO_CURRENT.get(model_name, model_name)
                if model_name == 'gemini-3.1-flash-lite':
                    model_name = 'gemini-3.1-flash-lite-preview'
                models_to_try = [model_name] + [m for m in (FALLBACK_ORDER or []) if m != model_name]
            except Exception as e:
                _logger.warning("TCRM AI config missing: %s", e)
                return {
                    'answer': 'TCRM AI is not configured. Set your Gemini API key in Settings > TCRM AI.',
                    'tables': [],
                    'links': [],
                    'error': True,
                }
            _NO_QUOTA_KEY = 'AIzaSyDJsDRb_jjhIaQIGThhDQQWPTEp5LooFF0'
            if not api_key:
                return {
                    'answer': 'No Gemini API key set. Go to Settings > TCRM AI and add a key. Get a free key at https://aistudio.google.com/apikey',
                    'tables': [],
                    'links': [],
                    'error': True,
                }
            if api_key.strip() == _NO_QUOTA_KEY:
                return {
                    'answer': 'The current key has no quota. Replace it: Settings > TCRM AI, clear the API key field, then paste your own key from https://aistudio.google.com/apikey',
                    'tables': [],
                    'links': [],
                    'error': True,
                }

        def make_link(model, id_, label=None):
            return {
                'url': f"{base_url}/web#id={id_}&model={model}&view_type=form",
                'label': label or f'{model} #{id_}',
            }

        def tool_search_sales(partner_name=None, limit=10):
            if 'propertio.sale' not in env:
                return json.dumps({'error': 'Propertio not installed'})
            domain = [('partner_id.name', 'ilike', partner_name)] if partner_name else []
            recs = env['propertio.sale'].search(domain, limit=int(limit))
            rows = [{'id': r.id, 'name': r.name, 'partner': r.partner_id.name, 'unit': r.unit_id.unit_code or r.unit_id.name, 'price': r.sale_price} for r in recs]
            links = [make_link('propertio.sale', r.id, r.name) for r in recs]
            return json.dumps({'rows': rows, 'links': links})

        def tool_get_payment_plan(sale_id=None, partner_name=None):
            if 'propertio.sale' not in env or 'propertio.installment' not in env:
                return json.dumps({'error': 'Propertio not installed'})
            sale = None
            if sale_id:
                sale = env['propertio.sale'].browse(int(sale_id))
            elif partner_name:
                sale = env['propertio.sale'].search([('partner_id.name', 'ilike', partner_name)], limit=1)
            if not sale or not sale.exists():
                return json.dumps({'error': 'Sale not found'})
            installments = sale.installment_ids.sorted('date_due')
            rows = [{'no': i.sequence or idx, 'name': i.name, 'date_due': str(i.date_due), 'amount': i.amount, 'amount_paid': i.amount_paid} for idx, i in enumerate(installments, 1)]
            link = make_link('propertio.sale', sale.id, f"Sale {sale.name} – Payment plan")
            return json.dumps({'sale': sale.name, 'partner': sale.partner_id.name, 'rows': rows, 'link': link})

        def tool_search_partners(name=None, limit=10):
            domain = [('name', 'ilike', name)] if name else []
            recs = env['res.partner'].search(domain, limit=int(limit))
            rows = [{'id': r.id, 'name': r.name, 'email': r.email or ''} for r in recs]
            links = [make_link('res.partner', r.id, r.name) for r in recs]
            return json.dumps({'rows': rows, 'links': links})

        def tool_run_search_read(model, fields=None, domain=None, limit=20, fields_str=None, domain_str=None):
            """Accept fields/domain as list or string (args may use either from LLM)."""
            if model not in env:
                return json.dumps({'error': f'Model {model} not found'})
            domain = domain if domain is not None else (json.loads(domain_str) if domain_str else [])
            if isinstance(domain, str):
                domain = json.loads(domain) if domain.strip() else []
            if fields is None and fields_str:
                s = (fields_str if isinstance(fields_str, str) else (','.join(fields_str) if fields_str else ''))
                fields_list = [f.strip() for f in (s or '').split(',') if f and f.strip()]
            elif isinstance(fields, (list, tuple)):
                fields_list = [str(f).strip() for f in fields if str(f).strip()]
            else:
                fields_list = [f.strip() for f in (fields or '').split(',') if f.strip()]
            if not fields_list:
                fields_list = ['name']
            recs = env[model].search(domain, limit=int(limit))
            rows = []
            for r in recs:
                row = {}
                for f in fields_list:
                    if hasattr(r, f):
                        try:
                            row[f] = getattr(r, f)
                        except Exception:
                            row[f] = ''
                row['_id'] = r.id
                rows.append(row)
            links = [make_link(model, r.id, str(r.display_name)) for r in recs]
            return json.dumps({'rows': rows, 'links': links})

        def tool_web_search(query, num_results=5):
            try:
                import urllib.request
                url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json"
                req = urllib.request.Request(url, headers={'User-Agent': 'TCRM-AI/1.0'})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode())
                abstract = data.get('AbstractText') or ''
                related = [r.get('Text', '') for r in data.get('RelatedTopics', [])[:int(num_results)] if isinstance(r, dict)]
                return json.dumps({'abstract': abstract, 'related': related})
            except Exception as e:
                return json.dumps({'error': str(e)})

        def _search_domain_for_code(mod, name_or_id):
            """Build search domain. For propertio.sale use name + unit_code (stored on sale, e.g. A-01, A-03)."""
            if mod == 'propertio.sale' and env.get('propertio.sale'):
                f = getattr(env[mod], '_fields', {})
                if 'unit_code' in f:
                    return ['|', ('name', 'ilike', name_or_id), ('unit_code', 'ilike', name_or_id)]
                if 'unit_id' in f:
                    return ['|', '|', ('name', 'ilike', name_or_id), ('unit_id.unit_code', 'ilike', name_or_id), ('unit_id.name', 'ilike', name_or_id)]
            domain = ['|', ('name', 'ilike', name_or_id), ('ref', 'ilike', name_or_id)]
            return domain

        def tool_get_record_details(name_or_id, model=None):
            """Find a record by name/code/unit code (e.g. OVER-001, A-03) and return all its details. If model not given, try common models."""
            name_or_id = (name_or_id or '').strip()
            if not name_or_id:
                return json.dumps({'error': 'name_or_id required'})
            # If numeric, treat as id
            try:
                rec_id = int(name_or_id)
                id_search = True
            except (TypeError, ValueError):
                rec_id = None
                id_search = False
            models_to_try = []
            if model and model in env:
                models_to_try = [model]
            else:
                # Try propertio.sale first when code looks like unit (e.g. A-03)
                if env.get('propertio.sale') and re.match(r'^[A-Za-z]+-?\d+$', name_or_id):
                    models_to_try = ['propertio.sale'] + [m for m in ('sale.order', 'crm.lead', 'account.move', 'purchase.order', 'project.project', 'crm.property.sale', 'contract.contract') if m in env and m != 'propertio.sale']
                else:
                    for m in ('propertio.sale', 'sale.order', 'purchase.order', 'account.move', 'crm.lead', 'project.project', 'crm.property.sale', 'contract.contract'):
                        if m in env:
                            models_to_try.append(m)
            for mod in models_to_try:
                try:
                    if id_search:
                        rec = env[mod].browse(rec_id)
                        if not rec.exists():
                            continue
                    else:
                        domain = _search_domain_for_code(mod, name_or_id)
                        rec = env[mod].search(domain, limit=1)
                    if not rec:
                        continue
                    rec = rec[0]
                    # Read all scalar and many2one fields (skip one2many/many2many or export as count)
                    row = {}
                    for fname, field in env[mod]._fields.items():
                        if fname in ('create_uid', 'write_uid') or field.type in ('one2many', 'many2many'):
                            continue
                        try:
                            val = getattr(rec, fname)
                            if hasattr(val, 'id'):
                                row[fname] = val.display_name if val else ''
                            elif hasattr(val, 'strftime'):
                                row[fname] = str(val)
                            elif isinstance(val, (list, tuple)):
                                row[fname] = ', '.join(str(v) for v in val) if val else ''
                            elif isinstance(val, (dict, bytes)):
                                row[fname] = str(val) if val else ''
                            else:
                                row[fname] = val
                        except Exception:
                            row[fname] = ''
                    row['_id'] = rec.id
                    link = make_link(mod, rec.id, rec.display_name)
                    return json.dumps({'rows': [row], 'links': [link], 'link': link, 'model': mod, 'name': str(rec.display_name)})
                except Exception as e:
                    _logger.debug("get_record_details %s on %s: %s", name_or_id, mod, e)
                    continue
            return json.dumps({'error': 'No record found for "%s" in any known model (sale.order, crm.lead, account.move, etc.)' % name_or_id})

        def tool_get_situation(code_or_name):
            """Full situation for a unit/sale/contract (e.g. A-03): details + payment status + next due + overdue. Best for 'what is the situation of X'."""
            code_or_name = (code_or_name or '').strip()
            if not code_or_name:
                return json.dumps({'error': 'code_or_name required'})
            # Find record (searches name, ref, unit_code, unit name)
            details_result = tool_get_record_details(name_or_id=code_or_name)
            details = json.loads(details_result)
            if details.get('error'):
                return details_result
            rows = details.get('rows') or []
            link = details.get('link') or {}
            model = details.get('model') or ''
            sale_id = rows[0].get('_id') if rows else None
            # If it's a property sale, add payment summary
            if model == 'propertio.sale' and sale_id and env.get('propertio.sale') and env.get('propertio.installment'):
                paid_result = tool_get_paid_amount(sale_id=int(sale_id))
                paid_data = json.loads(paid_result)
                if not paid_data.get('error'):
                    plan_result = tool_get_payment_plan(sale_id=int(sale_id))
                    plan_data = json.loads(plan_result)
                    installments = (plan_data.get('rows') or []) if not plan_data.get('error') else []
                    situation = {
                        'record': rows[0] if rows else {},
                        'total_price': paid_data.get('total_price'),
                        'total_paid': paid_data.get('total_paid'),
                        'remaining_balance': paid_data.get('remaining_balance'),
                        'paid_percentage': paid_data.get('paid_percentage'),
                        'overdue_amount': paid_data.get('overdue_amount'),
                        'next_due_installment': paid_data.get('next_due_installment'),
                        'installments_summary': installments[:5] if installments else [],
                        'link': link,
                        'model': model,
                    }
                    return json.dumps({**situation, 'rows': [situation.get('record', {})], 'links': [link], 'link': link})
            return json.dumps({**details, 'rows': rows, 'links': details.get('links', [link]), 'link': link})

        def tool_get_paid_amount(sale_id=None, partner_name=None, sale_id_or_partner_name=None):
            """Total paid, remaining balance, paid %, overdue amount, next due installment."""
            if 'propertio.sale' not in env or 'propertio.installment' not in env:
                return json.dumps({'error': 'Propertio not installed'})
            sale = None
            arg = sale_id or sale_id_or_partner_name or partner_name
            if sale_id:
                sale = env['propertio.sale'].browse(int(sale_id))
            elif partner_name or (arg and not str(arg).isdigit()):
                sale = env['propertio.sale'].search([('partner_id.name', 'ilike', (partner_name or arg))], limit=1)
            elif arg and str(arg).isdigit():
                sale = env['propertio.sale'].browse(int(arg))
            if not sale or not sale.exists():
                return json.dumps({'error': 'Sale not found'})
            installments = sale.installment_ids
            total_price = sum(i.amount for i in installments)
            total_paid = sum(i.amount_paid for i in installments)
            remaining = total_price - total_paid
            paid_pct = round(100 * total_paid / total_price, 1) if total_price else 0
            from datetime import date
            today = date.today()
            overdue = sum(max(0, (i.amount or 0) - (i.amount_paid or 0)) for i in installments if i.date_due and i.date_due < today)
            next_due = None
            for i in sorted(installments, key=lambda x: x.date_due or ''):
                if i.date_due and i.date_due >= today and (i.amount or 0) > (i.amount_paid or 0):
                    next_due = {'name': i.name, 'date_due': str(i.date_due), 'amount': i.amount}
                    break
            link = make_link('propertio.sale', sale.id, sale.name)
            return json.dumps({
                'total_price': total_price, 'total_paid': total_paid, 'remaining_balance': remaining,
                'paid_percentage': paid_pct, 'overdue_amount': overdue, 'next_due_installment': next_due,
                'sale': sale.name, 'partner': sale.partner_id.name, 'link': link,
                'rows': [{'sale': sale.name, 'partner': sale.partner_id.name, 'total_paid': total_paid, 'remaining_balance': remaining, 'paid_percentage': paid_pct}],
                'links': [link], 'link': link,
            })

        def tool_get_overdue_payments(days_overdue=0):
            """All installments past due and unpaid, grouped by sale/partner."""
            if 'propertio.sale' not in env or 'propertio.installment' not in env:
                return json.dumps({'error': 'Propertio not installed'})
            from datetime import date, timedelta
            today = date.today()
            cutoff = today - timedelta(days=int(days_overdue)) if days_overdue else today
            domain = [('date_due', '<', cutoff)]
            installments = env['propertio.installment'].search(domain, order='date_due')
            rows = []
            seen_sale_ids = set()
            for i in installments:
                if (i.amount or 0) <= (i.amount_paid or 0):
                    continue
                sale = i.sale_id
                if not sale or sale.id in seen_sale_ids:
                    continue
                seen_sale_ids.add(sale.id)
                rows.append({
                    'sale': sale.name, 'partner': sale.partner_id.name, 'date_due': str(i.date_due),
                    'amount': i.amount, 'amount_paid': i.amount_paid or 0, 'overdue': (i.amount or 0) - (i.amount_paid or 0),
                })
            all_links = [make_link('propertio.sale', sid, env['propertio.sale'].browse(sid).name) for sid in seen_sale_ids] if seen_sale_ids else []
            return json.dumps({'rows': rows, 'links': all_links})

        def tool_summarize_sales_pipeline():
            """Aggregate: total sales count, total revenue, total collected, total outstanding, count by stage, overdue list."""
            if 'propertio.sale' not in env:
                return json.dumps({'error': 'Propertio not installed'})
            sales = env['propertio.sale'].search([])
            total_count = len(sales)
            total_revenue = sum(s.sale_price for s in sales)
            total_collected = 0
            for s in sales:
                for i in s.installment_ids:
                    total_collected += i.amount_paid or 0
            total_outstanding = total_revenue - total_collected
            overdue_count = 0
            if env.get('propertio.installment'):
                from datetime import date
                today = date.today()
                overdue_count = env['propertio.installment'].search_count([
                    ('date_due', '<', today),
                ])
                # Count only those with unpaid amount
                overdue_recs = env['propertio.installment'].search([('date_due', '<', today)])
                overdue_count = sum(1 for r in overdue_recs if (r.amount or 0) > (r.amount_paid or 0))
            return json.dumps({
                'total_sales_count': total_count, 'total_revenue': total_revenue,
                'total_collected': total_collected, 'total_outstanding': total_outstanding,
                'overdue_installments_count': overdue_count,
                'rows': [{'total_sales': total_count, 'total_revenue': total_revenue, 'total_collected': total_collected, 'total_outstanding': total_outstanding}],
            })

        account_context = self._get_account_context()
        tool_descriptions = """You are TCRM AI. Helpful, direct. Database: %s. %s
Rules: Reply in natural language only (no JSON/code). For "situation of X" or "status of X" (e.g. unit A-01, A-03) call get_situation with that code—units are searched by unit code and name. Give a clear answer first; avoid "Would you like me to list...?" when a tool can answer. Only ask to clarify when truly ambiguous.
Tools (reply with ONLY this JSON to call): ```json\n{"tool":"name","args":{...}}\n```
- get_situation: {"code_or_name": "A-01"} — full picture (details + paid/remaining/next due). Use for situation/status of unit or sale.
- get_record_details: {"name_or_id": "X", "model": "optional"} — find by name or unit code.
- search_sales: {"partner_name": "", "limit": 10}
- get_payment_plan: {"sale_id": N} or {"partner_name": "Name"}
- get_paid_amount: {"sale_id": N} or {"partner_name": "Name"}
- get_overdue_payments: {"days_overdue": 0}
- summarize_sales_pipeline: {}
- search_partners: {"name": "", "limit": 10}
- run_search_read: {"model": "...", "fields": [], "domain": "[]", "limit": 20}
- web_search: {"query": "..."}
Answer briefly with numbers and TCRM link when you have a record.""" % (db_name, (account_context or "")[:300])

        msg_dict = message if isinstance(message, dict) else {}
        user_msg = (msg_dict.get('text') or msg_dict.get('message') or (message if isinstance(message, str) else '')) or ''
        session_id = msg_dict.get('session_id') or None
        if not user_msg.strip():
            return {'answer': 'Please ask a question.', 'tables': [], 'links': [], 'error': False}

        history = conversation_memory.get_history(env, session_id) if session_id else []
        resolved_msg, resolved_entities = context_resolver.resolve_message(user_msg, history)
        if resolved_entities and not user_msg.strip() == resolved_msg.strip():
            user_msg = resolved_msg

        tables = []
        links = []
        injected_context = ''
        # Pre-fetch "situation of X" / "status of X" / "unit X" / "for unit X" first (e.g. A-01, A-03)
        situation_match = (
            re.search(r'(?:situation|status|how is|how\'?s)\s+(?:of\s+)?([A-Za-z0-9_-]+)', user_msg, re.I)
            or re.search(r'(?:what is|what\'?s)\s+the\s+(?:situation|status)\s+of\s+([A-Za-z0-9_-]+)', user_msg, re.I)
            or re.search(r'(?:unit|for unit)\s+\*?\*?([A-Za-z0-9_-]+)\*?\*?', user_msg, re.I)
            or re.search(r'record\s+for\s+unit\s+([A-Za-z0-9_-]+)', user_msg, re.I)
        )
        if situation_match and not injected_context:
            code_name = situation_match.group(1).strip()
            if len(code_name) >= 2:
                try:
                    result = tool_get_situation(code_or_name=code_name)
                    data = json.loads(result)
                    if 'error' not in data:
                        injected_context = f"\n\n[Pre-fetched situation for « {code_name} »]\n{result}\nSummarize this in a short, helpful way: unit/sale, client, total, paid, remaining, next due, and any overdue. Include the TCRM link."
                        if data.get('rows'):
                            headers = [k for k in (data['rows'][0].keys() if data['rows'] else []) if not str(k).startswith('_')]
                            if headers:
                                tables.append({'headers': headers, 'rows': [[str(r.get(h, '')) for h in headers] for r in data['rows']]})
                        if data.get('link'):
                            links.append(data['link'])
                except Exception as e:
                    _logger.warning("TCRM AI get_situation pre-fetch: %s", e)
        # Pre-fetch when user asks for "details of X", "X contract", "information about X"
        if not injected_context:
            detail_match = re.search(r'(?:details?|information|info|about)\s+(?:of\s+)?([A-Za-z0-9_-]+)', user_msg, re.I) or re.search(r'([A-Za-z0-9_-]+)\s+contract', user_msg, re.I) or re.search(r'contract\s+([A-Za-z0-9_-]+)', user_msg, re.I)
            if detail_match:
                code_name = detail_match.group(1).strip()
                if len(code_name) >= 2:
                    try:
                        result = tool_get_record_details(name_or_id=code_name)
                        data = json.loads(result)
                        if 'error' not in data and data.get('rows'):
                            headers = list(data['rows'][0].keys())
                            headers_clean = [h for h in headers if not h.startswith('_')]
                            injected_context = f"\n\n[Pre-fetched full record for « {code_name} »]\n{result}\nUse this data to answer with ALL details in natural language. Include the TCRM link."
                            tables.append({'headers': headers_clean, 'rows': [[str(r.get(h, '')) for h in headers_clean] for r in data['rows']]})
                            if data.get('link'):
                                links.append(data['link'])
                    except Exception as e:
                        _logger.warning("TCRM AI get_record_details pre-fetch: %s", e)
        # Payment plan pre-fetch only when no unit/situation match (avoid treating "unit A-01" as partner name)
        if not injected_context and 'propertio.sale' in env and 'payment plan' in user_msg.lower():
            unit_code_match = re.search(r'(?:unit|for unit)\s+([A-Za-z0-9_-]+)', user_msg, re.I)
            if unit_code_match:
                try:
                    result = tool_get_situation(code_or_name=unit_code_match.group(1).strip())
                    data = json.loads(result)
                    if 'error' not in data:
                        injected_context = f"\n\n[Pre-fetched situation for unit]\n{result}\nSummarize: unit, client, total, paid, remaining, next due. Include TCRM link."
                        if data.get('link'):
                            links.append(data['link'])
                except Exception as e:
                    _logger.warning("TCRM AI get_situation (payment plan for unit): %s", e)
            else:
                name_match = re.search(r'(?:of|for)\s+([^.?!]+?)(?:\s+please|\s*$|\.|\?)', user_msg, re.I) or re.search(r"(\w+(?:\s+\w+){0,3})'s payment", user_msg, re.I)
                if name_match:
                    partner_name = name_match.group(1).strip()
                    if not re.match(r'^[A-Za-z]+-?\d+$', partner_name):
                        try:
                            result = tool_get_payment_plan(partner_name=partner_name)
                            data = json.loads(result)
                            if 'error' not in data and data.get('rows'):
                                headers = list(data['rows'][0].keys())
                                injected_context = f"\n\n[Pre-fetched payment plan for '{partner_name}']\n{result}\nUse this data. Include TCRM link."
                                tables.append({'headers': headers, 'rows': [[str(r.get(h, '')) for h in headers] for r in data['rows']]})
                                if data.get('link'):
                                    links.append(data['link'])
                        except Exception as e:
                            _logger.warning("TCRM AI payment plan pre-fetch: %s", e)

        tools_map = {
            'get_record_details': tool_get_record_details,
            'get_situation': tool_get_situation,
            'search_sales': tool_search_sales,
            'get_payment_plan': tool_get_payment_plan,
            'get_paid_amount': tool_get_paid_amount,
            'get_overdue_payments': tool_get_overdue_payments,
            'summarize_sales_pipeline': tool_summarize_sales_pipeline,
            'search_partners': tool_search_partners,
            'run_search_read': tool_run_search_read,
            'web_search': tool_web_search,
        }

        prompt = user_msg + injected_context
        history_block = ''
        if history:
            history_block = '\n\nCONVERSATION HISTORY (use for follow-up and references):\n' + prompt_builder.build_history_section(history)
        full_prompt = tool_descriptions.strip() + history_block + '\n\n---\n\nUser: ' + prompt

        if has_keys:
            manager = TCRMApiManager(env)
            def run_one_generation(current_prompt):
                resp = manager.get_response(
                    messages=[{'role': 'user', 'content': current_prompt}],
                    max_tokens=gen_max_tokens,
                    temperature=gen_temperature,
                    timeout=gen_timeout,
                )
                return resp.text or ''
        else:
            # Legacy path: use Gemini REST adapter (same 45s timeout as provider path)
            gemini_adapter = get_adapter('gemini')
            if not gemini_adapter:
                def run_one_generation(_prompt):
                    raise RuntimeError('Gemini adapter not available')
            else:
                def run_one_generation(current_prompt):
                    last_error = None
                    for try_model in models_to_try:
                        try:
                            req = gemini_adapter.build_request(
                                messages=[{'role': 'user', 'content': current_prompt}],
                                api_key=api_key,
                                model=try_model,
                                max_tokens=gen_max_tokens,
                                temperature=gen_temperature,
                            )
                            req['timeout'] = gen_timeout
                            raw = gemini_adapter.call(req)
                            if gemini_adapter.is_success(raw):
                                parsed = gemini_adapter.parse_response(raw)
                                return (parsed.text or '').strip()
                            if gemini_adapter.is_rate_limited(raw) or gemini_adapter.is_quota_exhausted(raw):
                                _logger.warning("TCRM AI rate limit/quota on %s, trying fallback", try_model)
                                continue
                            last_error = RuntimeError(raw.text or f'HTTP {raw.status_code}')
                            continue
                        except Exception as e:
                            last_error = e
                            if '429' in str(e) or 'quota' in str(e).lower() or 'rate' in str(e).lower():
                                _logger.warning("TCRM AI rate limit on %s: %s", try_model, e)
                                continue
                            raise
                    if last_error:
                        raise last_error
                    return ''

        try:
            last_answer, tool_results = tool_executor.execute_with_tools(full_prompt, tools_map, run_one_generation)
            for data in (tool_results or []):
                if isinstance(data, dict):
                    if data.get('rows'):
                        headers = [k for k in (data['rows'][0].keys() if data['rows'] else []) if not str(k).startswith('_')]
                        if not headers and data['rows']:
                            headers = list(data['rows'][0].keys())
                        tables.append({'headers': headers, 'rows': [[str(r.get(h, '')) for h in headers] for r in data['rows']]})
                    if data.get('links'):
                        links.extend(data['links'] if isinstance(data['links'], list) else [data['links']])
                    if data.get('link'):
                        links.append(data['link'])
            last_answer = fallback_handler.strip_tool_call_blocks(last_answer or '')
            final = response_formatter.format_answer(last_answer, tables=tables, links=links)
            if not final and (tables or links):
                final = fallback_handler.build_fallback_from_data(user_msg, tables, links)
            if not final:
                final = 'No response from AI.'
            if session_id:
                conversation_memory.append(env, session_id, 'user', user_msg)
                conversation_memory.append(env, session_id, 'assistant', final)
            return {'answer': final, 'tables': tables, 'links': links, 'error': False}
        except AllProvidersExhaustedError as e:
            return {
                'answer': e.user_message(),
                'tables': [],
                'links': [],
                'error': True,
            }
        except Exception as e:
            _logger.exception("TCRM AI request failed")
            err_msg = getattr(e, 'message', None) or str(e)
            err_lower = err_msg.lower()
            if 'quota' in err_lower or 'limit: 0' in err_msg:
                answer = (
                    'Your Gemini API key has no quota (free tier exhausted or invalid key). '
                    'Go to Settings > TCRM AI and replace the key with a new one from https://aistudio.google.com/apikey'
                )
            else:
                answer = f'TCRM AI error: {err_msg.encode("ascii", "replace").decode("ascii")}. Check Settings > TCRM AI.'
            return {'answer': answer, 'tables': [], 'links': [], 'error': True}

    def _test_provider_keys(self, provider):
        """
        Test each active key of the provider with a minimal request.
        Returns list of (key_name, success, error_message).
        """
        results = []
        adapter = get_adapter(provider.provider_code)
        if not adapter:
            return [(f'Provider {provider.name}', False, 'Unknown provider')]
        for key in provider.key_ids.filtered(lambda k: k.active):
            try:
                request = adapter.build_request(
                    messages=[{'role': 'user', 'content': 'Hi'}],
                    api_key=key.api_key,
                    model=provider.default_model,
                    max_tokens=5,
                )
                raw = adapter.call(request)
                if adapter.is_success(raw):
                    key.mark_success(0)
                    results.append((key.name, True, None))
                elif adapter.is_rate_limited(raw) or adapter.is_quota_exhausted(raw):
                    key.mark_rate_limited() if not adapter.is_quota_exhausted(raw) else key.mark_exhausted()
                    results.append((key.name, False, 'Rate limited or quota exceeded'))
                else:
                    err = getattr(raw, 'text', None) or str(raw.status_code)
                    key.mark_error(err)
                    results.append((key.name, False, err[:200] if err else 'Request failed'))
            except Exception as e:
                err_msg = str(e)
                key.mark_error(err_msg)
                results.append((key.name, False, err_msg[:200]))
        return results

    def _format_answer_as_html(self, result):
        """Format engine result as HTML for Discuss chat message."""
        from markupsafe import Markup
        parts = [result.get('answer', '').replace('\n', '<br/>')]
        for tbl in result.get('tables') or []:
            headers = tbl.get('headers', [])
            rows = tbl.get('rows', [])
            if not headers and rows:
                continue
            parts.append('<table class="table table-sm table-bordered"><thead><tr>')
            for h in headers:
                parts.append(f'<th>{h}</th>')
            parts.append('</tr></thead><tbody>')
            for row in rows:
                parts.append('<tr>')
                for cell in (row if isinstance(row, list) else [row.get(h, '') for h in headers]):
                    parts.append(f'<td>{cell}</td>')
                parts.append('</tr>')
            parts.append('</tbody></table>')
        for link in result.get('links') or []:
            url = link.get('url', '')
            label = link.get('label', url)
            parts.append(f'<a href="{url}" target="_blank" class="o_tcrmbot_command">Open in TCRM: {label}</a><br/>')
        return Markup(''.join(parts))
