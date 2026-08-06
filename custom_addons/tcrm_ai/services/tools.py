# Part of TCRM AI. See LICENSE for details.
"""
Approved read-only TCRM ORM tools.

Every tool uses the current request DB and authenticated user (no sudo bypass).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import timedelta

from tcrm import fields, _

from . import orm_business
from . import web_research

_logger = logging.getLogger(__name__)

MAX_ROWS = 50

# Never return these field names from flexible readers.
SECRET_FIELD_RE = re.compile(
    r'(password|passwd|secret|token|api_?key|private_?key|encryption|fernet|'
    r'smtp_pass|database\.secret|jdbc|dsn|connection_string|oauth|bearer)',
    re.I,
)

# OpenAI-compatible tool schemas exposed to Groq.
TOOL_DEFINITIONS = [
    {
        'type': 'function',
        'function': {
            'name': 'get_available_business_models',
            'description': 'List business models the current user may query via AI tools.',
            'parameters': {'type': 'object', 'properties': {}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_available_report_types',
            'description': 'List approved business report types available to this user.',
            'parameters': {'type': 'object', 'properties': {}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_business_records',
            'description': 'Search allowed business records with a safe domain (ACL + record rules).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string'},
                    'domain': {'type': 'array', 'items': {}},
                    'fields': {'type': 'array', 'items': {'type': 'string'}},
                    'limit': {'type': 'integer'},
                    'order': {'type': 'string'},
                },
                'required': ['model'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'read_business_record',
            'description': 'Read one allowed business record by id (safe fields only).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string'},
                    'record_id': {'type': 'integer'},
                    'fields': {'type': 'array', 'items': {'type': 'string'}},
                },
                'required': ['model', 'record_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'aggregate_business_records',
            'description': 'Deterministic count/sum/avg/min/max over allowed records.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string'},
                    'domain': {'type': 'array', 'items': {}},
                    'measure_field': {'type': 'string'},
                    'agg': {'type': 'string', 'enum': ['count', 'sum', 'avg', 'min', 'max']},
                },
                'required': ['model'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'group_business_records',
            'description': 'Group allowed records by a field with deterministic aggregates.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string'},
                    'domain': {'type': 'array', 'items': {}},
                    'group_by': {'type': 'string'},
                    'measure_field': {'type': 'string'},
                    'agg': {'type': 'string'},
                    'limit': {'type': 'integer'},
                },
                'required': ['model', 'group_by'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_business_report',
            'description': 'Build an approved business report from ORM aggregates.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'report_type': {'type': 'string'},
                    'days': {'type': 'integer'},
                },
                'required': ['report_type'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_lead_summary',
            'description': 'Aggregate CRM lead counts for a period (new leads, by stage).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'days': {'type': 'integer', 'description': 'Lookback days (default 30)'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_accessible_leads',
            'description': (
                'Search CRM leads by name, contact, email, or phone/mobile '
                '(supports TR formats like 05xx, +90, 90…).'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {'type': 'string'},
                    'limit': {'type': 'integer'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_lead_details',
            'description': 'Get one lead by id with safe CRM fields (no secrets).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'lead_id': {'type': 'integer'},
                },
                'required': ['lead_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_partners',
            'description': 'Search contacts/partners by name, phone, email or VAT.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {'type': 'string'},
                    'limit': {'type': 'integer'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'web_search',
            'description': 'Search the public web for news/facts (no secrets). For weather prefer get_weather.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {'type': 'string'},
                    'limit': {'type': 'integer'},
                },
                'required': ['query'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_weather',
            'description': 'Get live weather for a city (e.g. Istanbul, Ankara). Use for hava durumu questions.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'city': {'type': 'string', 'description': 'City name, default Istanbul'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_pipeline_summary',
            'description': 'CRM pipeline summary by stage.',
            'parameters': {'type': 'object', 'properties': {}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_sales_summary',
            'description': 'Property sales summary (propertio.sale).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'days': {'type': 'integer'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_payment_summary',
            'description': 'Deterministic payment/collection totals for a period.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'days': {'type': 'integer'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_overdue_payments',
            'description': 'Overdue installment residuals (exact amounts from ORM).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'limit': {'type': 'integer'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_collection_forecast',
            'description': 'Upcoming installment totals due in the next N days.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'days': {'type': 'integer'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_project_inventory',
            'description': 'Project unit inventory counts by state.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'project_name': {'type': 'string'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_available_units',
            'description': 'List available units, optionally filtered by project.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'project_name': {'type': 'string'},
                    'limit': {'type': 'integer'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_salesperson_performance',
            'description': 'Salesperson performance from confirmed sales.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'days': {'type': 'integer'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_marketing_performance',
            'description': 'Meta/marketing lead performance if marketing hub is installed.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'days': {'type': 'integer'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_call_center_statistics',
            'description': 'Call center (Santral) statistics for the current user scope.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'days': {'type': 'integer'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'generate_management_report',
            'description': 'Build a management report payload from verified tool aggregates.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'period_days': {'type': 'integer'},
                    'include_payments': {'type': 'boolean'},
                    'include_leads': {'type': 'boolean'},
                    'include_inventory': {'type': 'boolean'},
                },
            },
        },
    },
]


class ToolDenied(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class TcrmAiToolExecutor:
    def __init__(self, env, config, base_url: str = '', correlation_id: str = ''):
        self.env = env
        self.config = config
        self.base_url = (base_url or '').rstrip('/')
        self.correlation_id = (correlation_id or '')[:64]
        self.tools_used: list[str] = []
        self.references: list[dict] = []
        self._orm = orm_business.OrmBusinessTools(env, config, references=self.references)

    def _audit(self, tool_name: str, args: dict, ok: bool, detail: str = ''):
        try:
            self.env['tcrm.ai.audit'].sudo().create({
                'user_id': self.env.user.id,
                'company_id': self.env.company.id,
                'tool_name': tool_name,
                'arguments_safe': json.dumps({k: args.get(k) for k in (args or {}) if k != 'sql'}, default=str)[:2000],
                'success': ok,
                'detail': (detail or '')[:2000],
            })
        except Exception:
            _logger.debug('AI audit write skipped', exc_info=True)

    def _allow(self, flag: str) -> bool:
        return bool(getattr(self.config, flag, False))

    def _require(self, flag: str, label: str):
        if not self._allow(flag):
            raise ToolDenied(_('%s verisine erişim bu yapılandırmada kapalı.') % label)

    def _limit(self, limit, default=20):
        try:
            return max(1, min(MAX_ROWS, int(limit or default)))
        except Exception:
            return default

    def _days(self, days, default=30):
        try:
            return max(1, min(366, int(days or default)))
        except Exception:
            return default

    def _mask_email(self, email):
        if not email or not self.config.mask_personal_data:
            return email or ''
        parts = str(email).split('@')
        if len(parts) != 2:
            return '•••'
        name = parts[0]
        return (name[:1] + '•••@' + parts[1]) if name else '•••@' + parts[1]

    def _mask_phone(self, phone):
        if not phone or not self.config.mask_personal_data:
            return phone or ''
        text = str(phone)
        if len(text) <= 4:
            return '••••'
        return '••••' + text[-4:]

    def _link(self, model, res_id, label):
        if not self.base_url:
            return {'model': model, 'id': res_id, 'label': label}
        return {
            'model': model,
            'id': res_id,
            'label': label,
            'url': '%s/web#id=%s&model=%s&view_type=form' % (self.base_url, res_id, model),
        }

    def available_tool_defs(self) -> list[dict]:
        allowed = set()
        # Generic safe ORM surface whenever any business capability is on.
        if any(self._allow(f) for f in (
            'allow_crm_data', 'allow_sales_data', 'allow_property_data',
            'allow_payment_data', 'allow_reports',
        )):
            allowed |= {
                'get_available_business_models',
                'search_business_records',
                'read_business_record',
                'aggregate_business_records',
                'group_business_records',
                'get_available_report_types',
                'get_business_report',
            }
        if self._allow('allow_crm_data'):
            allowed |= {
                'get_lead_summary', 'search_accessible_leads', 'get_lead_details',
                'search_partners', 'get_pipeline_summary',
                'get_marketing_performance', 'get_call_center_statistics',
            }
        if self._allow('allow_sales_data'):
            allowed |= {'get_sales_summary', 'get_salesperson_performance'}
        if self._allow('allow_property_data'):
            allowed |= {'get_project_inventory', 'get_available_units'}
        if self._allow('allow_payment_data'):
            allowed |= {'get_payment_summary', 'get_overdue_payments', 'get_collection_forecast'}
        if self._allow('allow_reports'):
            allowed |= {'generate_management_report'}
        if self._allow('allow_internet_research') and getattr(self.config, 'search_enabled', True):
            allowed |= {'web_search', 'get_weather'}
        return [t for t in TOOL_DEFINITIONS if t['function']['name'] in allowed]

    @staticmethod
    def _digits_only(value: str) -> str:
        return re.sub(r'\D', '', value or '')

    def _phone_variants(self, query: str) -> list[str]:
        digits = self._digits_only(query)
        if len(digits) < 7:
            return []
        variants = {digits, query.strip()}
        if digits.startswith('90') and len(digits) >= 12:
            local = digits[2:]
            variants.update({local, '0' + local, '+' + digits, '90' + local})
        if digits.startswith('0') and len(digits) >= 10:
            bare = digits[1:]
            variants.update({bare, '90' + bare, '+90' + bare})
        if len(digits) >= 10:
            last10 = digits[-10:]
            variants.update({last10, '0' + last10, '90' + last10, '+90' + last10})
        # Drop empty / tiny noise
        return [v for v in variants if v and (not v.isdigit() or len(v) >= 7)]

    def _or_domain(self, leaves: list) -> list:
        """Build an OR domain from leaf triples [('f','ilike',v), ...]."""
        leaves = [leaf for leaf in leaves if leaf]
        if not leaves:
            return []
        if len(leaves) == 1:
            return [leaves[0]]
        return (['|'] * (len(leaves) - 1)) + list(leaves)

    def execute(self, name: str, arguments: dict | None) -> str:
        args = arguments or {}
        # Hard reject dangerous payloads
        banned = {'sql', 'query_sql', 'database', 'db_name', 'dbname', 'sudo', 'shell', 'code', 'python'}
        if banned.intersection(set(args.keys())):
            self._audit(name, args, False, 'banned_args')
            raise ToolDenied(_('Yetkisiz araç parametresi.'))
        if name not in {t['function']['name'] for t in self.available_tool_defs()}:
            self._audit(name, args, False, 'not_allowed')
            raise ToolDenied(_('Bu araç kullanımına izin verilmiyor.'))
        handler = getattr(self, name, None)
        if not handler:
            self._audit(name, args, False, 'missing_handler')
            raise ToolDenied(_('Araç bulunamadı.'))
        try:
            # Generic ORM tools delegate to OrmBusinessTools
            if name in {
                'get_available_business_models', 'get_available_report_types',
                'search_business_records', 'read_business_record',
                'aggregate_business_records', 'group_business_records',
                'get_business_report',
            }:
                result = getattr(self._orm, name)(**args)
            else:
                result = handler(**args)
            self.tools_used.append(name)
            self._audit(name, args, True, detail='cid=%s' % self.correlation_id)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except ToolDenied:
            raise
        except PermissionError as exc:
            self._audit(name, args, False, 'permission')
            raise ToolDenied(str(exc) or _('Bu veri için yetkiniz yok.')) from exc
        except Exception as exc:
            _logger.warning(
                'TCRM AI tool %s failed cid=%s err=%s',
                name, self.correlation_id or '-', type(exc).__name__,
            )
            self._audit(name, args, False, type(exc).__name__)
            return json.dumps({'error': _('Araç çalıştırılamadı.'), 'tool': name})

    # ── Tools ──────────────────────────────────────────────────────

    def get_lead_summary(self, days=30):
        self._require('allow_crm_data', 'CRM')
        Lead = self.env['crm.lead']
        days = self._days(days)
        since = fields.Date.context_today(Lead) - timedelta(days=days)
        domain = [('create_date', '>=', fields.Datetime.to_string(
            fields.Datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=days)
        ))]
        total = Lead.search_count([])
        new_count = Lead.search_count(domain)
        won = Lead.search_count([('probability', '=', 100), ('date_closed', '>=', since)]) if 'date_closed' in Lead._fields else 0
        return {
            'period_days': days,
            'company': self.env.company.name,
            'currency': self.env.company.currency_id.name,
            'total_leads_accessible': total,
            'new_leads': new_count,
            'won_in_period': won,
            'data_source': 'crm.lead',
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
        }

    def search_accessible_leads(self, query=None, limit=20):
        self._require('allow_crm_data', 'CRM')
        Lead = self.env['crm.lead']
        limit = self._limit(limit)
        domain = []
        q = (query or '').strip()
        if q:
            leaves = [
                ('name', 'ilike', q),
                ('contact_name', 'ilike', q),
                ('partner_name', 'ilike', q),
                ('email_from', 'ilike', q),
            ]
            Partner = self.env['res.partner']
            phone_fields = [
                f for f in ('phone', 'mobile', 'phone_sanitized', 'partner_phone')
                if f in Lead._fields
            ]
            if 'partner_id' in Lead._fields:
                for f in ('phone', 'mobile', 'phone_sanitized'):
                    if f in Partner._fields:
                        phone_fields.append('partner_id.%s' % f)
            for variant in self._phone_variants(q):
                for field_name in phone_fields:
                    leaves.append((field_name, 'ilike', variant))
            digits = self._digits_only(q)
            if len(digits) >= 10:
                tail = digits[-10:]
                for field_name in phone_fields:
                    leaves.append((field_name, 'ilike', tail))
            domain = self._or_domain(leaves)
        leads = Lead.search(domain, limit=limit, order='write_date desc, create_date desc')
        # Extra pass: digit-normalized match when ORM ilike missed formatting noise
        if q and self._digits_only(q) and len(leads) < limit:
            Partner = self.env['res.partner']
            want = self._digits_only(q)
            tails = {want[-10:]} if len(want) >= 10 else {want}
            if want.startswith('0') and len(want) >= 11:
                tails.add(want[1:][-10:] if len(want[1:]) >= 10 else want[1:])
            extra = Lead.search([], limit=min(500, MAX_ROWS * 10), order='write_date desc')
            found_ids = set(leads.ids)
            for lead in extra:
                if lead.id in found_ids:
                    continue
                parts = []
                if 'phone' in Lead._fields:
                    parts.append(lead.phone or '')
                if 'mobile' in Lead._fields:
                    parts.append(lead.mobile or '')
                if lead.partner_id:
                    if 'phone' in Partner._fields:
                        parts.append(lead.partner_id.phone or '')
                    if 'mobile' in Partner._fields:
                        parts.append(lead.partner_id.mobile or '')
                blob = self._digits_only(' '.join(parts))
                if any(t and t in blob for t in tails):
                    leads |= lead
                    found_ids.add(lead.id)
                    if len(found_ids) >= limit:
                        break
            leads = leads[:limit]
        rows = []
        for lead in leads:
            rows.append({
                'id': lead.id,
                'name': lead.name,
                'stage': lead.stage_id.name if lead.stage_id else '',
                'user': lead.user_id.name if lead.user_id else '',
                'email': self._mask_email(lead.email_from),
                'phone': self._mask_phone(lead.phone or lead.mobile),
                'partner': lead.partner_id.name if lead.partner_id else '',
                'create_date': str(lead.create_date or ''),
            })
            self.references.append(self._link('crm.lead', lead.id, lead.name))
        return {
            'query': q,
            'record_count': len(rows),
            'rows': rows,
            'links': self.references[-len(rows):],
            'data_source': 'crm.lead',
            'company': self.env.company.name,
            'user': self.env.user.name,
            'generated_at': fields.Datetime.now(),
        }

    def get_lead_details(self, lead_id=None):
        self._require('allow_crm_data', 'CRM')
        if not lead_id:
            return {'error': 'lead_id gerekli', 'record_count': 0}
        lead = self.env['crm.lead'].browse(int(lead_id))
        if not lead.exists():
            return {'error': 'Lead bulunamadı veya erişilemez', 'record_count': 0}
        data = {
            'id': lead.id,
            'name': lead.name,
            'contact_name': lead.contact_name or '',
            'partner_name': lead.partner_name or '',
            'partner': lead.partner_id.name if lead.partner_id else '',
            'email': self._mask_email(lead.email_from),
            'phone': self._mask_phone(getattr(lead, 'phone', None)),
            'mobile': self._mask_phone(getattr(lead, 'mobile', None) if 'mobile' in lead._fields else None),
            'stage': lead.stage_id.name if lead.stage_id else '',
            'user': lead.user_id.name if lead.user_id else '',
            'team': lead.team_id.name if lead.team_id else '',
            'source': lead.source_id.name if lead.source_id else '',
            'priority': lead.priority if 'priority' in lead._fields else '',
            'expected_revenue': float(lead.expected_revenue or 0) if 'expected_revenue' in lead._fields else 0,
            'probability': float(lead.probability or 0) if 'probability' in lead._fields else 0,
            'description': (lead.description or '')[:2000] if lead.description else '',
            'create_date': str(lead.create_date or ''),
        }
        self.references.append(self._link('crm.lead', lead.id, lead.name))
        return {
            'record_count': 1,
            'lead': data,
            'links': self.references[-1:],
            'data_source': 'crm.lead',
            'company': self.env.company.name,
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
        }

    def search_partners(self, query=None, limit=20):
        self._require('allow_crm_data', 'CRM')
        Partner = self.env['res.partner']
        limit = self._limit(limit)
        q = (query or '').strip()
        domain = [('type', '!=', 'private')] if 'type' in Partner._fields else []
        if q:
            leaves = [
                ('name', 'ilike', q),
                ('email', 'ilike', q),
                ('vat', 'ilike', q),
                ('ref', 'ilike', q),
            ]
            partner_phone_fields = [f for f in ('phone', 'mobile') if f in Partner._fields]
            for variant in self._phone_variants(q):
                for field_name in partner_phone_fields:
                    leaves.append((field_name, 'ilike', variant))
            digits = self._digits_only(q)
            if len(digits) >= 10:
                for field_name in partner_phone_fields:
                    leaves.append((field_name, 'ilike', digits[-10:]))
            domain = domain + self._or_domain(leaves) if domain else self._or_domain(leaves)
        partners = Partner.search(domain, limit=limit, order='write_date desc')
        if q and self._digits_only(q) and len(partners) < limit:
            want = self._digits_only(q)
            tail = want[-10:] if len(want) >= 10 else want
            extra = Partner.search([('type', '!=', 'private')] if 'type' in Partner._fields else [], limit=400)
            found = set(partners.ids)
            for partner in extra:
                if partner.id in found:
                    continue
                parts = []
                if 'phone' in Partner._fields:
                    parts.append(partner.phone or '')
                if 'mobile' in Partner._fields:
                    parts.append(partner.mobile or '')
                blob = self._digits_only(''.join(parts))
                if tail and tail in blob:
                    partners |= partner
                    found.add(partner.id)
                    if len(found) >= limit:
                        break
            partners = partners[:limit]
        rows = []
        for partner in partners:
            phone_val = ''
            if 'phone' in Partner._fields:
                phone_val = partner.phone or ''
            if not phone_val and 'mobile' in Partner._fields:
                phone_val = partner.mobile or ''
            rows.append({
                'id': partner.id,
                'name': partner.name,
                'email': self._mask_email(partner.email),
                'phone': self._mask_phone(phone_val),
                'city': partner.city or '',
                'is_company': bool(partner.is_company),
                'vat': partner.vat or '',
            })
            self.references.append(self._link('res.partner', partner.id, partner.name))
        return {
            'query': q,
            'record_count': len(rows),
            'rows': rows,
            'links': self.references[-len(rows):],
            'data_source': 'res.partner',
            'company': self.env.company.name,
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
        }

    def _search_settings(self):
        cfg = self.config
        allowed = [
            d.strip() for d in (getattr(cfg, 'search_allowed_domains', '') or '').split(',')
            if d.strip()
        ]
        blocked = [
            d.strip() for d in (getattr(cfg, 'search_blocked_domains', '') or '').split(',')
            if d.strip()
        ]
        api_key = ''
        try:
            if hasattr(cfg, '_get_plaintext_search_api_key'):
                api_key = cfg._get_plaintext_search_api_key() or ''
        except Exception:
            api_key = ''
        return {
            'provider': getattr(cfg, 'search_provider', None) or 'duckduckgo',
            'api_key': api_key,
            'timeout': getattr(cfg, 'search_timeout', None) or 12,
            'max_results': getattr(cfg, 'search_max_results', None) or 5,
            'allowed_domains': allowed,
            'blocked_domains': blocked,
        }

    def get_weather(self, city=None):
        self._require('allow_internet_research', 'İnternet araştırması')
        if not getattr(self.config, 'search_enabled', True):
            raise ToolDenied(_('İnternet araştırması kapalı.'))
        city = (city or 'Istanbul').strip() or 'Istanbul'
        # Normalize common TR city mentions
        qlow = city.lower()
        for token in ('istanbul', 'ankara', 'izmir', 'antalya', 'bursa', 'adana'):
            if token in qlow:
                city = token
                break
        settings = self._search_settings()
        result = web_research.get_weather(city, timeout=settings['timeout'])
        if not result.get('ok'):
            return {
                'error': 'Hava durumu alınamadı',
                'city': city,
                'record_count': 0,
                'source_type': 'internet',
                'note': 'Şehri İngilizce veya Türkçe tekrar deneyin (Istanbul, Ankara…).',
            }
        for cite in result.get('citations') or []:
            if cite.get('url'):
                self.references.append({
                    'label': cite.get('title') or cite['url'],
                    'url': cite['url'],
                    'source_type': 'internet',
                })
        return {
            'city': city,
            'record_count': 1,
            'summary': result.get('summary'),
            'url': result.get('url'),
            'citations': result.get('citations') or [],
            'data_source': 'internet',
            'source_type': 'internet',
            'retrieved_at': result.get('retrieved_at'),
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
            'note': (
                'Bu sonuç İnternet kaynaklarından alındı (TCRM verisi değil). '
                'Özeti kullanıcıya aktar ve kaynak URL’sini belirt.'
            ),
        }

    def web_search(self, query=None, limit=5):
        self._require('allow_internet_research', 'İnternet araştırması')
        if not getattr(self.config, 'search_enabled', True):
            raise ToolDenied(_('İnternet araştırması kapalı.'))
        q = (query or '').strip()
        if not q:
            return {'error': 'query gerekli', 'record_count': 0}
        if SECRET_FIELD_RE.search(q) or any(
            bad in q.lower() for bad in ('password', 'api key', 'secret', 'credential', 'ssh key')
        ):
            raise ToolDenied(_('Gizli bilgi araması engellendi.'))
        settings = self._search_settings()
        # Weather-shaped queries: prefer live weather tool path.
        qlow = q.lower()
        if any(h in qlow for h in ('hava', 'weather', 'sıcak', 'sicak', 'yağmur', 'yagmur')):
            city = 'Istanbul'
            for token in ('istanbul', 'ankara', 'izmir', 'antalya', 'bursa', 'adana'):
                if token in qlow:
                    city = token
                    break
            weather = self.get_weather(city=city)
            if weather.get('summary'):
                return {
                    'query': q,
                    'record_count': 1,
                    'rows': [{
                        'title': 'Hava durumu — %s' % city,
                        'snippet': weather.get('summary'),
                        'url': weather.get('url'),
                    }],
                    'citations': weather.get('citations') or [],
                    'abstract': weather.get('summary'),
                    'data_source': 'internet',
                    'source_type': 'internet',
                    'retrieved_at': weather.get('retrieved_at'),
                    'generated_at': fields.Datetime.now(),
                    'user': self.env.user.name,
                    'note': 'İnternet kaynakları — TCRM verisi değil. Kaynakları alıntıla.',
                }
        limit = max(1, min(8, int(limit or settings['max_results'])))
        result = web_research.web_search(
            q,
            provider=settings['provider'],
            api_key=settings['api_key'],
            limit=limit,
            timeout=settings['timeout'],
            allowed_domains=settings['allowed_domains'],
            blocked_domains=settings['blocked_domains'],
        )
        for cite in result.get('citations') or []:
            if cite.get('url'):
                self.references.append({
                    'label': cite.get('title') or cite['url'],
                    'url': cite['url'],
                    'source_type': 'internet',
                })
        result['generated_at'] = fields.Datetime.now()
        result['user'] = self.env.user.name
        result['note'] = (
            'Bu sonuçlar İnternet kaynaklarından alındı (TCRM verisi değil). '
            'Cevapta tıklanabilir kaynak URL’lerini belirt.'
        )
        return result

    def get_pipeline_summary(self):
        self._require('allow_crm_data', 'CRM')
        Lead = self.env['crm.lead']
        Stage = self.env['crm.stage']
        stages = Stage.search([])
        rows = []
        for stage in stages:
            count = Lead.search_count([('stage_id', '=', stage.id)])
            rows.append({'stage': stage.name, 'count': count})
        return {
            'rows': rows,
            'record_count': sum(r['count'] for r in rows),
            'data_source': 'crm.lead',
            'company': self.env.company.name,
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
        }

    def get_sales_summary(self, days=30):
        self._require('allow_sales_data', 'Satış')
        if 'propertio.sale' not in self.env:
            return {'error': 'propertio.sale yüklü değil', 'record_count': 0}
        Sale = self.env['propertio.sale']
        days = self._days(days)
        since = fields.Date.context_today(Sale) - timedelta(days=days)
        domain = [('date_order', '>=', since)] if 'date_order' in Sale._fields else []
        if 'state' in Sale._fields:
            domain = domain + [('state', '=', 'confirmed')] if domain else [('state', '=', 'confirmed')]
        sales = Sale.search(domain, limit=500)
        total = sum(sales.mapped('sale_price')) if 'sale_price' in Sale._fields else 0.0
        currency = self.env.company.currency_id.name
        if sales and 'currency_id' in Sale._fields and sales[0].currency_id:
            currency = sales[0].currency_id.name
        return {
            'period_days': days,
            'filters': {'state': 'confirmed'},
            'company': self.env.company.name,
            'currency': currency,
            'sale_count': len(sales),
            'total_sale_price': float(total),
            'data_source': 'propertio.sale',
            'record_count': len(sales),
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
        }

    def get_payment_summary(self, days=30):
        self._require('allow_payment_data', 'Ödeme')
        if 'propertio.payment' not in self.env:
            return {'error': 'propertio.payment yüklü değil', 'record_count': 0}
        Payment = self.env['propertio.payment']
        days = self._days(days)
        since = fields.Date.context_today(Payment) - timedelta(days=days)
        domain = [('payment_date', '>=', since), ('state', '=', 'posted')]
        payments = Payment.search(domain, limit=2000)
        # Deterministic ORM totals — never ask the model to sum.
        total_amount = float(sum(payments.mapped('amount')))
        total_covered = float(sum(payments.mapped('covered_amount'))) if 'covered_amount' in Payment._fields else total_amount
        currency = self.env.company.currency_id.name
        return {
            'period_days': days,
            'filters': {'state': 'posted', 'payment_date_gte': str(since)},
            'company': self.env.company.name,
            'currency': currency,
            'payment_count': len(payments),
            'total_amount': total_amount,
            'total_covered_amount': total_covered,
            'data_source': 'propertio.payment',
            'record_count': len(payments),
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
            'note': 'Totals calculated by TCRM ORM tool; do not recalculate.',
        }

    def get_overdue_payments(self, limit=30):
        self._require('allow_payment_data', 'Ödeme')
        if 'propertio.installment' not in self.env:
            return {'error': 'propertio.installment yüklü değil', 'record_count': 0}
        Inst = self.env['propertio.installment']
        limit = self._limit(limit, 30)
        domain = [('payment_status', '=', 'overdue')]
        rows_recs = Inst.search(domain, limit=limit, order='date_due asc')
        total_residual = float(sum(rows_recs.mapped('residual')))
        rows = []
        for inst in rows_recs:
            rows.append({
                'id': inst.id,
                'name': inst.name,
                'partner': inst.partner_id.name if inst.partner_id else '',
                'date_due': str(inst.date_due or ''),
                'amount': float(inst.amount or 0),
                'residual': float(inst.residual or 0),
                'overdue_days': int(inst.overdue_days or 0) if 'overdue_days' in Inst._fields else 0,
                'currency': inst.currency_id.name if inst.currency_id else self.env.company.currency_id.name,
            })
            self.references.append(self._link('propertio.installment', inst.id, inst.name))
        return {
            'filters': {'payment_status': 'overdue'},
            'company': self.env.company.name,
            'currency': self.env.company.currency_id.name,
            'total_residual': total_residual,
            'rows': rows,
            'record_count': len(rows),
            'data_source': 'propertio.installment',
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
            'note': 'Totals calculated by TCRM ORM tool; do not recalculate.',
        }

    def get_collection_forecast(self, days=30):
        self._require('allow_payment_data', 'Ödeme')
        if 'propertio.installment' not in self.env:
            return {'error': 'propertio.installment yüklü değil', 'record_count': 0}
        Inst = self.env['propertio.installment']
        days = self._days(days)
        today = fields.Date.context_today(Inst)
        until = today + timedelta(days=days)
        domain = [
            ('is_paid', '=', False),
            ('date_due', '>=', today),
            ('date_due', '<=', until),
        ]
        recs = Inst.search(domain, limit=2000)
        total = float(sum(recs.mapped('residual')))
        return {
            'period_days': days,
            'filters': {'is_paid': False, 'date_due_lte': str(until)},
            'company': self.env.company.name,
            'currency': self.env.company.currency_id.name,
            'installment_count': len(recs),
            'forecast_residual_total': total,
            'data_source': 'propertio.installment',
            'record_count': len(recs),
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
            'note': 'Totals calculated by TCRM ORM tool; do not recalculate.',
        }

    def get_project_inventory(self, project_name=None):
        self._require('allow_property_data', 'Proje')
        if 'propertio.unit' not in self.env:
            return {'error': 'propertio.unit yüklü değil', 'record_count': 0}
        Unit = self.env['propertio.unit']
        Project = self.env['propertio.project'] if 'propertio.project' in self.env else None
        domain = []
        if project_name and Project is not None:
            projects = Project.search([('name', 'ilike', project_name)], limit=20)
            domain = [('project_id', 'in', projects.ids)]
        rows = []
        projects = Project.search([('id', 'in', Unit.search(domain).mapped('project_id').ids)], limit=50) if Project else []
        if not projects and Project is not None:
            projects = Project.search([('name', 'ilike', project_name)] if project_name else [], limit=50)
        for project in projects:
            units = Unit.search([('project_id', '=', project.id)])
            rows.append({
                'project': project.name,
                'available': len(units.filtered(lambda u: u.state == 'available')),
                'option': len(units.filtered(lambda u: u.state == 'option')),
                'sold': len(units.filtered(lambda u: u.state == 'sold')),
                'handover': len(units.filtered(lambda u: u.state == 'handover')),
                'total': len(units),
            })
        return {
            'filters': {'project_name': project_name or ''},
            'company': self.env.company.name,
            'rows': rows,
            'record_count': len(rows),
            'data_source': 'propertio.unit',
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
        }

    def get_available_units(self, project_name=None, limit=30):
        self._require('allow_property_data', 'Proje')
        if 'propertio.unit' not in self.env:
            return {'error': 'propertio.unit yüklü değil', 'record_count': 0}
        Unit = self.env['propertio.unit']
        limit = self._limit(limit, 30)
        domain = [('state', '=', 'available')]
        if project_name:
            domain.append(('project_id.name', 'ilike', project_name))
        units = Unit.search(domain, limit=limit)
        rows = []
        for u in units:
            rows.append({
                'id': u.id,
                'name': u.name,
                'unit_code': u.unit_code or '',
                'project': u.project_id.name if u.project_id else '',
                'list_price': float(u.list_price or 0),
                'currency': u.currency_id.name if u.currency_id else self.env.company.currency_id.name,
            })
            self.references.append(self._link('propertio.unit', u.id, u.display_name))
        return {
            'filters': {'state': 'available', 'project_name': project_name or ''},
            'rows': rows,
            'record_count': len(rows),
            'company': self.env.company.name,
            'data_source': 'propertio.unit',
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
        }

    def get_salesperson_performance(self, days=30):
        self._require('allow_sales_data', 'Satış')
        if 'propertio.sale' not in self.env:
            return {'error': 'propertio.sale yüklü değil', 'record_count': 0}
        Sale = self.env['propertio.sale']
        days = self._days(days)
        since = fields.Date.context_today(Sale) - timedelta(days=days)
        domain = [('state', '=', 'confirmed')]
        if 'date_order' in Sale._fields:
            domain.append(('date_order', '>=', since))
        sales = Sale.search(domain, limit=2000)
        by_user = {}
        for sale in sales:
            uid = sale.sales_person_id if 'sales_person_id' in Sale._fields else sale.user_id if 'user_id' in Sale._fields else False
            key = uid.name if uid else _('Atanmamış')
            bucket = by_user.setdefault(key, {'sales_count': 0, 'total_sale_price': 0.0})
            bucket['sales_count'] += 1
            bucket['total_sale_price'] += float(getattr(sale, 'sale_price', 0) or 0)
        rows = [{'salesperson': k, **v} for k, v in sorted(by_user.items(), key=lambda x: -x[1]['total_sale_price'])]
        return {
            'period_days': days,
            'rows': rows,
            'record_count': len(sales),
            'company': self.env.company.name,
            'currency': self.env.company.currency_id.name,
            'data_source': 'propertio.sale',
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
            'note': 'Totals calculated by TCRM ORM tool; do not recalculate.',
        }

    def get_marketing_performance(self, days=30):
        self._require('allow_crm_data', 'CRM')
        days = self._days(days)
        since_dt = fields.Datetime.now() - timedelta(days=days)
        if 'tcrm.marketing.meta.lead' in self.env:
            Meta = self.env['tcrm.marketing.meta.lead']
            domain = [('create_date', '>=', fields.Datetime.to_string(since_dt))]
            leads = Meta.search(domain, limit=2000)
            by_campaign = {}
            for lead in leads:
                key = lead.campaign_name or _('Kampanyasız')
                by_campaign[key] = by_campaign.get(key, 0) + 1
            rows = [{'campaign': k, 'lead_count': v} for k, v in sorted(by_campaign.items(), key=lambda x: -x[1])]
            return {
                'period_days': days,
                'rows': rows,
                'record_count': len(leads),
                'company': self.env.company.name,
                'data_source': 'tcrm.marketing.meta.lead',
                'generated_at': fields.Datetime.now(),
                'user': self.env.user.name,
            }
        # Fallback: crm.lead with marketing fields
        Lead = self.env['crm.lead']
        domain = [('create_date', '>=', fields.Datetime.to_string(since_dt))]
        if 'mh_campaign_name' in Lead._fields:
            leads = Lead.search(domain + [('mh_campaign_name', '!=', False)], limit=2000)
            by_campaign = {}
            for lead in leads:
                key = lead.mh_campaign_name or _('Kampanyasız')
                by_campaign[key] = by_campaign.get(key, 0) + 1
            rows = [{'campaign': k, 'lead_count': v} for k, v in sorted(by_campaign.items(), key=lambda x: -x[1])]
            return {
                'period_days': days,
                'rows': rows,
                'record_count': len(leads),
                'company': self.env.company.name,
                'data_source': 'crm.lead',
                'generated_at': fields.Datetime.now(),
                'user': self.env.user.name,
            }
        return {'error': 'Marketing hub verisi yok', 'record_count': 0}

    def get_call_center_statistics(self, days=30):
        self._require('allow_crm_data', 'CRM')
        if 'tcrm.call.record' not in self.env:
            return {'error': 'tcrm.call.record yüklü değil', 'record_count': 0}
        Call = self.env['tcrm.call.record']
        days = self._days(days)
        since_dt = fields.Datetime.now() - timedelta(days=days)
        calls = Call.search([('create_date', '>=', fields.Datetime.to_string(since_dt))], limit=5000)
        by_outcome = {}
        for call in calls:
            key = dict(call._fields['outcome'].selection).get(call.outcome, call.outcome) if 'outcome' in Call._fields and call.outcome else _('Belirsiz')
            by_outcome[key] = by_outcome.get(key, 0) + 1
        return {
            'period_days': days,
            'total_calls': len(calls),
            'by_outcome': [{'outcome': k, 'count': v} for k, v in sorted(by_outcome.items(), key=lambda x: -x[1])],
            'company': self.env.company.name,
            'data_source': 'tcrm.call.record',
            'record_count': len(calls),
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
        }

    def generate_management_report(self, period_days=30, include_payments=True, include_leads=True, include_inventory=True):
        self._require('allow_reports', 'Rapor')
        days = self._days(period_days)
        sections = {}
        if include_leads and self._allow('allow_crm_data'):
            sections['leads'] = self.get_lead_summary(days=days)
        if include_payments and self._allow('allow_payment_data'):
            sections['payments'] = self.get_payment_summary(days=days)
            sections['overdue'] = self.get_overdue_payments(limit=20)
        if include_inventory and self._allow('allow_property_data'):
            sections['inventory'] = self.get_project_inventory()
        if self._allow('allow_sales_data'):
            sections['sales'] = self.get_sales_summary(days=days)
        report = {
            'title': _('Yönetim Raporu'),
            'report_period_days': days,
            'filters': {
                'include_payments': bool(include_payments),
                'include_leads': bool(include_leads),
                'include_inventory': bool(include_inventory),
            },
            'company': self.env.company.name,
            'generation_date': fields.Datetime.now(),
            'data_source': 'TCRM ORM tools',
            'record_count': sum(int(s.get('record_count') or 0) for s in sections.values() if isinstance(s, dict)),
            'currency': self.env.company.currency_id.name,
            'user': self.env.user.name,
            'sections': sections,
        }
        if self.config.save_conversation_history:
            try:
                self.env['tcrm.ai.report'].create({
                    'name': '%s — %s' % (_('Yönetim Raporu'), fields.Date.context_today(self.env['tcrm.ai.report'])),
                    'company_id': self.env.company.id,
                    'user_id': self.env.user.id,
                    'period_days': days,
                    'payload_json': json.dumps(report, default=str),
                    'currency_id': self.env.company.currency_id.id,
                    'record_count': report['record_count'],
                })
            except Exception:
                _logger.debug('report persist skipped', exc_info=True)
        return report
