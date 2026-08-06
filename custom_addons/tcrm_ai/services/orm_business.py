# Part of TCRM AI. See LICENSE for details.
"""Safe generic read-only ORM tools for installed TCRM business apps."""
from __future__ import annotations

import logging
import re
from datetime import timedelta

from tcrm import fields, _

_logger = logging.getLogger(__name__)

MAX_ROWS = 50
MAX_AGG_GROUPS = 40
ALLOWED_OPS = {
    '=', '!=', '>', '>=', '<', '<=', 'like', 'ilike', 'in', 'not in',
    'child_of', '=like', '=ilike',
}

# Never expose these models via generic tools.
DENIED_MODELS = {
    'ir.config_parameter',
    'ir.logging',
    'ir.attachment',
    'ir.rule',
    'ir.model.access',
    'ir.model.data',
    'ir.module.module',
    'res.users',
    'res.users.apikeys',
    'res.users.apikeys.description',
    'res.users.log',
    'res.groups',
    'bus.presence',
    'mail.guest',
    'auth_totp.device',
    'auth_oauth.provider',
    'fetchmail.server',
    'ir.mail_server',
    'tcrm.ai.config',
    'tcrm.ai.key',
    'tcrm.ai.provider',
    'tcrm.ai.usage',
    'tcrm.ai.audit',
    'tcrm.tenant',
    'tcrm.tenant.ai.status',
    'tcrm.tenant.module.entitlement',
    'tcrm.provisioning.job',
    'tcrm.saas.package',
}

SECRET_FIELD_RE = re.compile(
    r'(password|passwd|secret|token|api_?key|private_?key|encryption|fernet|'
    r'smtp_pass|database\.secret|jdbc|dsn|connection_string|oauth|bearer|'
    r'signature|ssh|certificate)',
    re.I,
)

# Model → capability flag on tcrm.ai.config
MODEL_CAPABILITY = {
    'crm.lead': 'allow_crm_data',
    'crm.stage': 'allow_crm_data',
    'crm.team': 'allow_crm_data',
    'res.partner': 'allow_crm_data',
    'calendar.event': 'allow_crm_data',
    'mail.activity': 'allow_crm_data',
    'project.project': 'allow_crm_data',
    'project.task': 'allow_crm_data',
    'hr.employee': 'allow_crm_data',
    'sale.order': 'allow_sales_data',
    'sale.order.line': 'allow_sales_data',
    'propertio.sale': 'allow_sales_data',
    'propertio.project': 'allow_property_data',
    'propertio.unit': 'allow_property_data',
    'propertio.block': 'allow_property_data',
    'propertio.payment': 'allow_payment_data',
    'propertio.installment': 'allow_payment_data',
    'account.move': 'allow_payment_data',
    'account.payment': 'allow_payment_data',
}

REPORT_TYPES = [
    {'code': 'lead_summary', 'label': 'Lead özeti', 'capability': 'allow_crm_data'},
    {'code': 'pipeline_summary', 'label': 'Pipeline özeti', 'capability': 'allow_crm_data'},
    {'code': 'sales_summary', 'label': 'Satış özeti', 'capability': 'allow_sales_data'},
    {'code': 'payment_summary', 'label': 'Ödeme özeti', 'capability': 'allow_payment_data'},
    {'code': 'inventory_summary', 'label': 'Stok / birim özeti', 'capability': 'allow_property_data'},
    {'code': 'management_report', 'label': 'Yönetim raporu', 'capability': 'allow_reports'},
]


def _module_installed(env, technical_name: str) -> bool:
    Module = env['ir.module.module'].sudo()
    mod = Module.search([('name', '=', technical_name)], limit=1)
    return bool(mod and mod.state == 'installed')


def discover_business_models(env, config) -> list[dict]:
    """Build allowlist from installed apps + explicit metadata (no full ir.model dump)."""
    candidates = []

    def add(model, label, capability, category):
        if model in DENIED_MODELS:
            return
        if model not in env:
            return
        if not getattr(config, capability, False):
            return
        # ACL check for current user
        try:
            env[model].check_access('read')
        except Exception:
            return
        candidates.append({
            'model': model,
            'label': label,
            'category': category,
            'capability': capability,
        })

    if 'crm.lead' in env:
        add('crm.lead', 'CRM Lead / Fırsat', 'allow_crm_data', 'CRM')
        add('crm.stage', 'CRM Aşama', 'allow_crm_data', 'CRM')
        add('crm.team', 'CRM Ekip', 'allow_crm_data', 'CRM')
    add('res.partner', 'Kişiler / Kontaklar', 'allow_crm_data', 'Contacts')
    if 'calendar.event' in env:
        add('calendar.event', 'Takvim', 'allow_crm_data', 'Calendar')
    if 'mail.activity' in env:
        add('mail.activity', 'Aktiviteler', 'allow_crm_data', 'Activities')
    if 'project.project' in env:
        add('project.project', 'Projeler', 'allow_crm_data', 'Projects')
        add('project.task', 'Görevler', 'allow_crm_data', 'Projects')
    if 'hr.employee' in env:
        add('hr.employee', 'Çalışanlar', 'allow_crm_data', 'HR')
    if 'sale.order' in env:
        add('sale.order', 'Satış Siparişleri', 'allow_sales_data', 'Sales')
    if 'propertio.sale' in env:
        add('propertio.sale', 'Gayrimenkul Satışları', 'allow_sales_data', 'Sales')
    if 'propertio.project' in env:
        add('propertio.project', 'Gayrimenkul Projeleri', 'allow_property_data', 'Property')
        add('propertio.unit', 'Birimler', 'allow_property_data', 'Property')
    if 'propertio.payment' in env:
        add('propertio.payment', 'Ödemeler', 'allow_payment_data', 'Payments')
        add('propertio.installment', 'Taksitler', 'allow_payment_data', 'Payments')
    if 'account.move' in env and _module_installed(env, 'account'):
        add('account.move', 'Faturalar', 'allow_payment_data', 'Invoicing')
        add('account.payment', 'Muhasebe Ödemeleri', 'allow_payment_data', 'Invoicing')
    return candidates


class OrmBusinessTools:
    def __init__(self, env, config, references: list | None = None):
        self.env = env
        self.config = config
        self.references = references if references is not None else []

    def _allowed_models(self) -> dict[str, dict]:
        return {m['model']: m for m in discover_business_models(self.env, self.config)}

    def _require_model(self, model_name: str):
        model_name = (model_name or '').strip()
        if not model_name or model_name in DENIED_MODELS:
            raise PermissionError(_('Bu modele erişim engellendi.'))
        allowed = self._allowed_models()
        if model_name not in allowed:
            raise PermissionError(_('Model izin listesinde değil veya yüklü değil.'))
        Model = self.env[model_name]
        Model.check_access('read')
        return Model, allowed[model_name]

    def _safe_fields(self, Model, requested: list[str] | None) -> list[str]:
        fields_map = Model._fields
        if requested:
            names = [f for f in requested if f in fields_map and not SECRET_FIELD_RE.search(f)]
        else:
            preferred = [
                'name', 'display_name', 'partner_id', 'user_id', 'stage_id', 'state',
                'create_date', 'write_date', 'date_order', 'amount_total', 'expected_revenue',
                'email_from', 'phone', 'mobile', 'city', 'date_deadline', 'priority',
            ]
            names = [f for f in preferred if f in fields_map and not SECRET_FIELD_RE.search(f)]
            if not names:
                names = [
                    f for f, field in fields_map.items()
                    if field.store and field.type in ('char', 'text', 'integer', 'float', 'monetary', 'boolean', 'date', 'datetime', 'selection', 'many2one')
                    and not SECRET_FIELD_RE.search(f)
                ][:12]
        # Always drop password-like / binary
        out = []
        for name in names[:20]:
            field = fields_map.get(name)
            if not field:
                continue
            if field.type in ('binary', 'html'):
                continue
            if getattr(field, 'groups', None) and 'base.group_system' in (field.groups or ''):
                continue
            out.append(name)
        return out or ['display_name'] if 'display_name' in fields_map else list(fields_map)[:1]

    def _sanitize_domain(self, Model, domain) -> list:
        if not domain:
            return []
        if not isinstance(domain, list):
            raise ValueError('domain_invalid')
        if len(domain) > 40:
            raise ValueError('domain_too_large')
        clean = []
        for item in domain:
            if item in ('|', '&', '!'):
                clean.append(item)
                continue
            if not (isinstance(item, (list, tuple)) and len(item) == 3):
                raise ValueError('domain_leaf_invalid')
            field_name, op, value = item
            if not isinstance(field_name, str) or '.' in field_name and field_name.count('.') > 1:
                raise ValueError('relation_depth')
            root = field_name.split('.')[0]
            if root not in Model._fields or SECRET_FIELD_RE.search(field_name):
                raise ValueError('field_denied')
            if op not in ALLOWED_OPS:
                raise ValueError('operator_denied')
            if isinstance(value, str) and len(value) > 200:
                value = value[:200]
            if isinstance(value, (list, tuple)) and len(value) > 50:
                value = list(value)[:50]
            clean.append((field_name, op, value))
        return clean

    def _serialize_record(self, rec, field_names: list[str]) -> dict:
        row = {'id': rec.id}
        for name in field_names:
            field = rec._fields.get(name)
            if not field:
                continue
            val = rec[name]
            if field.type == 'many2one':
                row[name] = val.display_name if val else ''
            elif field.type in ('one2many', 'many2many'):
                row[name] = len(val)
            elif field.type == 'binary':
                continue
            else:
                row[name] = val if not hasattr(val, 'isoformat') else str(val)
        return row

    def get_available_business_models(self):
        models = discover_business_models(self.env, self.config)
        return {
            'record_count': len(models),
            'rows': models,
            'data_source': 'tcrm_allowlist',
            'company': self.env.company.name,
            'user': self.env.user.name,
            'generated_at': fields.Datetime.now(),
            'note': 'Only these models may be queried. Access still follows ACLs and record rules.',
        }

    def get_available_report_types(self):
        rows = []
        for item in REPORT_TYPES:
            if getattr(self.config, item['capability'], False):
                rows.append({'code': item['code'], 'label': item['label']})
        return {
            'record_count': len(rows),
            'rows': rows,
            'data_source': 'tcrm_reports',
            'generated_at': fields.Datetime.now(),
        }

    def search_business_records(self, model=None, domain=None, fields=None, limit=20, order=None):
        Model, meta = self._require_model(model)
        limit = max(1, min(MAX_ROWS, int(limit or 20)))
        domain = self._sanitize_domain(Model, domain)
        field_names = self._safe_fields(Model, fields)
        order_by = 'id desc'
        if order and isinstance(order, str) and re.match(r'^[\w.\s,]+$', order):
            order_by = order[:80]
        recs = Model.search(domain, limit=limit, order=order_by)
        rows = [self._serialize_record(r, field_names) for r in recs]
        for r in recs:
            label = r.display_name if 'display_name' in r._fields else ('%s,%s' % (model, r.id))
            self.references.append({'model': model, 'id': r.id, 'label': label})
        return {
            'model': model,
            'category': meta.get('category'),
            'record_count': len(rows),
            'rows': rows,
            'fields': field_names,
            'data_source': 'tcrm_orm',
            'company': self.env.company.name,
            'user': self.env.user.name,
            'generated_at': fields.Datetime.now(),
        }

    def read_business_record(self, model=None, record_id=None, fields=None):
        Model, meta = self._require_model(model)
        if not record_id:
            return {'error': 'record_id gerekli', 'record_count': 0}
        rec = Model.browse(int(record_id))
        if not rec.exists():
            return {'error': 'Kayıt bulunamadı veya erişilemez', 'record_count': 0}
        field_names = self._safe_fields(Model, fields)
        data = self._serialize_record(rec, field_names)
        self.references.append({
            'model': model,
            'id': rec.id,
            'label': rec.display_name if 'display_name' in rec._fields else str(rec.id),
        })
        return {
            'model': model,
            'category': meta.get('category'),
            'record_count': 1,
            'record': data,
            'data_source': 'tcrm_orm',
            'company': self.env.company.name,
            'user': self.env.user.name,
            'generated_at': fields.Datetime.now(),
        }

    def aggregate_business_records(self, model=None, domain=None, measure_field=None, agg='count'):
        Model, meta = self._require_model(model)
        domain = self._sanitize_domain(Model, domain)
        agg = (agg or 'count').lower()
        if agg not in ('count', 'sum', 'avg', 'min', 'max'):
            raise ValueError('agg_denied')
        if agg == 'count':
            value = Model.search_count(domain)
            return {
                'model': model,
                'aggregation': 'count',
                'value': value,
                'company': self.env.company.name,
                'data_source': 'tcrm_orm_deterministic',
                'note': 'Exact count from ORM. Do not recalculate.',
                'generated_at': fields.Datetime.now(),
                'user': self.env.user.name,
            }
        measure_field = (measure_field or '').strip()
        field = Model._fields.get(measure_field)
        if not field or field.type not in ('integer', 'float', 'monetary') or SECRET_FIELD_RE.search(measure_field):
            raise ValueError('measure_denied')
        recs = Model.search(domain, limit=5000)
        values = [float(v or 0) for v in recs.mapped(measure_field)]
        if not values:
            result = 0.0
        elif agg == 'sum':
            result = sum(values)
        elif agg == 'avg':
            result = sum(values) / len(values)
        elif agg == 'min':
            result = min(values)
        else:
            result = max(values)
        return {
            'model': model,
            'aggregation': agg,
            'measure_field': measure_field,
            'value': float(result),
            'record_count': len(values),
            'company': self.env.company.name,
            'currency': self.env.company.currency_id.name,
            'data_source': 'tcrm_orm_deterministic',
            'note': 'Exact aggregate from ORM. Explain this value; do not recalculate.',
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
        }

    def group_business_records(self, model=None, domain=None, group_by=None, measure_field=None, agg='count', limit=20):
        Model, meta = self._require_model(model)
        domain = self._sanitize_domain(Model, domain)
        group_by = (group_by or '').strip()
        if not group_by or group_by not in Model._fields or SECRET_FIELD_RE.search(group_by):
            raise ValueError('group_by_denied')
        limit = max(1, min(MAX_AGG_GROUPS, int(limit or 20)))
        # Prefer read_group when available
        measure_field = (measure_field or '').strip()
        agg = (agg or 'count').lower()
        if hasattr(Model, 'read_group'):
            fields_arg = ['__count']
            if measure_field and measure_field in Model._fields and Model._fields[measure_field].type in ('integer', 'float', 'monetary'):
                fields_arg = ['%s:%s' % (measure_field, agg if agg != 'count' else 'sum')]
            grouped = Model.read_group(domain, fields_arg, [group_by], limit=limit)
            rows = []
            for g in grouped:
                key = g.get(group_by)
                if isinstance(key, (list, tuple)):
                    key = key[1] if len(key) > 1 else key[0]
                value = g.get(measure_field) if measure_field and measure_field in g else g.get(group_by + '_count') or g.get('__count') or g.get(list(g.keys())[-1])
                rows.append({'group': key, 'value': value})
            return {
                'model': model,
                'group_by': group_by,
                'aggregation': agg,
                'rows': rows,
                'record_count': len(rows),
                'data_source': 'tcrm_orm_deterministic',
                'company': self.env.company.name,
                'generated_at': fields.Datetime.now(),
                'user': self.env.user.name,
            }
        # Fallback: manual grouping
        recs = Model.search(domain, limit=2000)
        buckets = {}
        for rec in recs:
            val = rec[group_by]
            if hasattr(val, 'display_name'):
                key = val.display_name
            else:
                key = str(val or '')
            buckets.setdefault(key, []).append(rec)
        rows = []
        for key, items in list(buckets.items())[:limit]:
            if agg == 'count' or not measure_field:
                rows.append({'group': key, 'value': len(items)})
            else:
                nums = [float(i[measure_field] or 0) for i in items]
                rows.append({'group': key, 'value': sum(nums)})
        return {
            'model': model,
            'group_by': group_by,
            'rows': rows,
            'record_count': len(rows),
            'data_source': 'tcrm_orm_deterministic',
            'company': self.env.company.name,
            'generated_at': fields.Datetime.now(),
            'user': self.env.user.name,
        }

    def get_business_report(self, report_type=None, days=30):
        report_type = (report_type or '').strip()
        days = max(1, min(366, int(days or 30)))
        available = {r['code'] for r in self.get_available_report_types()['rows']}
        if report_type not in available:
            return {'error': 'Rapor tipi yok veya kapalı', 'record_count': 0}
        since = fields.Datetime.now() - timedelta(days=days)
        if report_type == 'lead_summary' and 'crm.lead' in self.env:
            Lead = self.env['crm.lead']
            Lead.check_access('read')
            total = Lead.search_count([])
            new_count = Lead.search_count([('create_date', '>=', fields.Datetime.to_string(since))])
            return {
                'report_type': report_type,
                'period_days': days,
                'total_leads_accessible': total,
                'new_leads': new_count,
                'data_source': 'tcrm_orm_deterministic',
                'company': self.env.company.name,
                'user': self.env.user.name,
                'generated_at': fields.Datetime.now(),
            }
        if report_type == 'pipeline_summary' and 'crm.lead' in self.env:
            Lead = self.env['crm.lead']
            Stage = self.env['crm.stage']
            Lead.check_access('read')
            rows = [{'stage': s.name, 'count': Lead.search_count([('stage_id', '=', s.id)])} for s in Stage.search([])]
            return {
                'report_type': report_type,
                'rows': rows,
                'data_source': 'tcrm_orm_deterministic',
                'company': self.env.company.name,
                'generated_at': fields.Datetime.now(),
            }
        return {
            'report_type': report_type,
            'period_days': days,
            'note': 'Bu rapor tipi için özel araçları (get_payment_summary vb.) kullanın.',
            'record_count': 0,
            'generated_at': fields.Datetime.now(),
        }
