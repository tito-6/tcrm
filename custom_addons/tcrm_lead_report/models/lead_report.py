# -*- coding: utf-8 -*-
"""Lead Raporu — consolidated dashboard aggregation service."""
from __future__ import annotations

import base64
import csv
import io
import logging
from collections import defaultdict
from datetime import datetime, time, timedelta

from tcrm import api, fields, models, _
from tcrm.exceptions import AccessError, UserError
from tcrm.tools import format_datetime, formatLang

from .status_map import CATEGORY_LABELS, CATEGORY_SELECTION

_logger = logging.getLogger(__name__)

ATTEMPT_STATUSES = (
    'initiated', 'ringing', 'in-progress', 'completed', 'busy', 'no-answer',
)


class TcrmLeadReport(models.AbstractModel):
    _name = 'tcrm.lead.report'
    _description = 'Lead Raporu Dashboard Service'

    # ------------------------------------------------------------------ helpers
    @api.model
    def _company(self):
        return self.env.company

    @api.model
    def _can_view_spend(self):
        return self.env.user.has_group('tcrm_lead_report.group_lead_report_spend')

    @api.model
    def _can_sync_marketing(self):
        return self.env.user.has_group('tcrm_marketing_hub.group_marketing_manager')

    @api.model
    def _parse_date(self, value):
        if not value:
            return False
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            return fields.Date.from_string(value[:10])
        return value

    @api.model
    def _datetime_bounds(self, date_from, date_to):
        """Convert inclusive local-date range to UTC-naive datetimes for create_date filter."""
        d0 = self._parse_date(date_from)
        d1 = self._parse_date(date_to)
        if not d0 or not d1:
            return False, False
        if d0 > d1:
            d0, d1 = d1, d0
        try:
            from zoneinfo import ZoneInfo
            from datetime import timezone
            tz_name = self.env.user.tz or 'UTC'
            tz = ZoneInfo(tz_name)
            start_local = datetime.combine(d0, time.min).replace(tzinfo=tz)
            end_local = datetime.combine(d1, time.max).replace(tzinfo=tz)
            start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
            end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
            return start_utc, end_utc
        except Exception:
            return datetime.combine(d0, time.min), datetime.combine(d1, time.max)

    @api.model
    def _pct(self, part, whole):
        if not whole:
            return None
        return round((part / whole) * 100, 1)

    @api.model
    def _safe_div(self, numerator, denominator):
        if not denominator:
            return None
        return round(numerator / denominator, 2)

    @api.model
    def _kpi(self, key, label, count, total, drill_key=None, tooltip=None):
        return {
            'key': key,
            'label': label,
            'count': count,
            'percent': self._pct(count, total),
            'drill_key': drill_key or key,
            'tooltip': tooltip or '',
        }

    @api.model
    def _build_cohort_domain(self, filters):
        """Build crm.lead domain for cohort (create_date + optional filters)."""
        Lead = self.env['crm.lead']
        domain = []
        if 'company_id' in Lead._fields:
            domain.append(('company_id', 'in', self.env.companies.ids))

        dt_start, dt_end = self._datetime_bounds(
            filters.get('date_from'), filters.get('date_to')
        )
        if dt_start and dt_end:
            domain.extend([
                ('create_date', '>=', fields.Datetime.to_string(dt_start)),
                ('create_date', '<=', fields.Datetime.to_string(dt_end)),
            ])

        if filters.get('source_id'):
            domain.append(('source_id', '=', int(filters['source_id'])))
        if filters.get('user_id'):
            domain.append(('user_id', '=', int(filters['user_id'])))
        if filters.get('team_id'):
            domain.append(('team_id', '=', int(filters['team_id'])))
        if filters.get('stage_id'):
            domain.append(('stage_id', '=', int(filters['stage_id'])))
        if filters.get('tag_id'):
            domain.append(('tag_ids', 'in', [int(filters['tag_id'])]))
        if filters.get('platform'):
            # mh_source_platform is computed — filter via meta lead join
            meta_leads = self.env['tcrm.marketing.meta.lead'].search([
                ('crm_lead_id', '!=', False),
                ('source_platform', 'ilike', filters['platform']),
            ])
            domain.append(('id', 'in', meta_leads.mapped('crm_lead_id').ids or [0]))
        if filters.get('campaign_id_remote'):
            meta_leads = self.env['tcrm.marketing.meta.lead'].search([
                ('campaign_id_remote', '=', str(filters['campaign_id_remote'])),
                ('crm_lead_id', '!=', False),
            ])
            domain.append(('id', 'in', meta_leads.mapped('crm_lead_id').ids or [0]))
        if filters.get('ad_id'):
            meta_leads = self.env['tcrm.marketing.meta.lead'].search([
                ('ad_id', '=', str(filters['ad_id'])),
                ('crm_lead_id', '!=', False),
            ])
            domain.append(('id', 'in', meta_leads.mapped('crm_lead_id').ids or [0]))
        if filters.get('project_id') and 'propertio_project_id' in Lead._fields:
            domain.append(('propertio_project_id', '=', int(filters['project_id'])))
        return domain

    @api.model
    def _cohort_leads(self, filters, limit=None):
        domain = self._build_cohort_domain(filters)
        return self.env['crm.lead'].search(domain, limit=limit, order='create_date desc')

    @api.model
    def _called_lead_ids(self, cohort_ids):
        if not cohort_ids:
            return set()
        Call = self.env['tcrm.call.record']
        santral_ids = set(
            Call.search([
                ('lead_id', 'in', list(cohort_ids)),
                ('direction', '=', 'outbound'),
                ('status', 'in', ATTEMPT_STATUSES),
            ]).mapped('lead_id').ids
        )
        state_ids = set(
            self.env['crm.lead'].search([
                ('id', 'in', list(cohort_ids)),
                ('call_follow_up_state', '=', 'called'),
            ]).ids
        )
        return santral_ids | state_ids

    @api.model
    def _answered_lead_ids(self, cohort_ids):
        if not cohort_ids:
            return set()
        Call = self.env['tcrm.call.record']
        answered = set()
        calls = Call.search([
            ('lead_id', 'in', list(cohort_ids)),
            ('direction', '=', 'outbound'),
        ])
        for call in calls:
            if call.answer_time:
                answered.add(call.lead_id.id)
            elif call.status == 'in-progress':
                answered.add(call.lead_id.id)
            elif call.status == 'completed' and call.duration > 0:
                answered.add(call.lead_id.id)
        return answered

    @api.model
    def _today_lead_count(self, cohort_domain):
        today = fields.Date.context_today(self)
        dt_start, dt_end = self._datetime_bounds(today, today)
        domain = list(cohort_domain)
        domain.extend([
            ('create_date', '>=', fields.Datetime.to_string(dt_start)),
            ('create_date', '<=', fields.Datetime.to_string(dt_end)),
        ])
        return self.env['crm.lead'].search_count(domain)

    @api.model
    def _first_call_metrics(self, cohort_ids):
        if not cohort_ids or 'tcrm.call.record' not in self.env:
            return {'avg_first_call_minutes': None, 'within_15_pct': None}
        Call = self.env['tcrm.call.record']
        calls = Call.search([
            ('lead_id', 'in', list(cohort_ids)),
            ('direction', '=', 'outbound'),
            ('status', 'in', ATTEMPT_STATUSES),
        ], order='start_time asc, create_date asc')
        first_by_lead = {}
        for call in calls:
            lid = call.lead_id.id
            if lid not in first_by_lead:
                ts = call.start_time or call.create_date
                if ts:
                    first_by_lead[lid] = ts
        if not first_by_lead:
            return {'avg_first_call_minutes': None, 'within_15_pct': None}
        Lead = self.env['crm.lead'].browse(list(first_by_lead.keys()))
        deltas = []
        within_15 = 0
        for lead in Lead:
            first_call = first_by_lead.get(lead.id)
            if not first_call or not lead.create_date:
                continue
            delta = (first_call - lead.create_date).total_seconds() / 60.0
            if delta < 0:
                delta = 0
            deltas.append(delta)
            if delta <= 15:
                within_15 += 1
        avg_min = round(sum(deltas) / len(deltas), 1) if deltas else None
        within_pct = round((within_15 / len(deltas)) * 100, 1) if deltas else None
        return {
            'avg_first_call_minutes': avg_min,
            'within_15_pct': within_pct,
        }

    @api.model
    def _timeline_bucket(self, date_from, date_to):
        d0 = self._parse_date(date_from)
        d1 = self._parse_date(date_to)
        if not d0 or not d1:
            return 'day'
        days = (d1 - d0).days + 1
        if days <= 2:
            return 'hour'
        if days <= 62:
            return 'day'
        if days <= 366:
            return 'week'
        return 'month'

    @api.model
    def _build_timeline(self, filters, called_ids, category_counts):
        domain = self._build_cohort_domain(filters)
        bucket = self._timeline_bucket(filters.get('date_from'), filters.get('date_to'))
        Lead = self.env['crm.lead']
        group_field = f'create_date:{bucket}'
        try:
            groups = Lead.read_group(
                domain,
                ['create_date:count'],
                [group_field],
                lazy=False,
            )
        except Exception:
            groups = Lead.read_group(
                domain,
                ['create_date'],
                ['create_date'],
                lazy=False,
            )
            group_field = 'create_date'
        points = []
        for g in groups:
            label = g.get(group_field)
            if isinstance(label, (list, tuple)):
                continue
            count_key = 'create_date_count' if 'create_date_count' in g else '__count'
            points.append({
                'label': str(label) if label else _('Diğer'),
                'leads': g.get(count_key, 0),
            })
        return {'bucket': bucket, 'points': points}

    @api.model
    def _build_sources(self, filters, cohort_ids, called_ids, category_by_lead):
        domain = self._build_cohort_domain(filters)
        groups = self.env['crm.lead'].read_group(
            domain,
            ['source_id'],
            ['source_id'],
            lazy=False,
        )
        total = len(cohort_ids) or sum(g.get('source_id_count', 0) for g in groups)
        rows = []
        for g in groups:
            src = g.get('source_id')
            name = src[1] if src else _('Bilinmiyor')
            src_id = src[0] if src else False
            count = g.get('source_id_count', 0)
            lead_subset = self.env['crm.lead'].search(
                domain + ([('source_id', '=', src_id)] if src_id else [('source_id', '=', False)])
            )
            subset_ids = set(lead_subset.ids)
            called = len(subset_ids & called_ids)
            cats = defaultdict(int)
            for lid in subset_ids:
                cat = category_by_lead.get(lid)
                if cat:
                    cats[cat] += 1
            rows.append({
                'source_id': src_id,
                'source': name,
                'leads': count,
                'percent': self._pct(count, total),
                'called': called,
                'uncalled': count - called,
                'positive': cats.get('positive', 0),
                'negative': cats.get('negative', 0),
                'appointment': cats.get('appointment', 0),
                'sales': cats.get('sale', 0),
                'drill_key': 'source',
                'drill_value': src_id or False,
            })
        rows.sort(key=lambda r: r['leads'], reverse=True)
        return rows

    @api.model
    def _build_campaigns(self, filters, cohort_ids, called_ids, category_by_lead):
        leads = self.env['crm.lead'].browse(list(cohort_ids))
        groups = defaultdict(lambda: {'name': '', 'lead_ids': set()})
        for lead in leads:
            camp_id = lead.mh_campaign_id_remote or ''
            if camp_id:
                key = camp_id
                name = lead.mh_campaign_name or camp_id
            else:
                key = '__unknown__'
                name = _('Attribution Unknown')
            groups[key]['name'] = name
            groups[key]['lead_ids'].add(lead.id)

        rows = []
        for camp_id, info in groups.items():
            subset_ids = info['lead_ids']
            count = len(subset_ids)
            camp_name = info['name']
            real_camp_id = camp_id if camp_id != '__unknown__' else False
            called = len(subset_ids & called_ids)
            cats = defaultdict(int)
            for lid in subset_ids:
                cat = category_by_lead.get(lid)
                if cat:
                    cats[cat] += 1
            spend = 0.0
            currency = False
            if self._can_view_spend() and real_camp_id and 'tcrm.marketing.daily.metric' in self.env:
                spend, currency = self.env['tcrm.marketing.daily.metric']._spend_for_campaign(
                    self._company().id,
                    real_camp_id,
                    filters.get('date_from'),
                    filters.get('date_to'),
                )
            rows.append({
                'campaign_id': real_camp_id or False,
                'campaign': camp_name,
                'leads': count,
                'called': called,
                'positive': cats.get('positive', 0),
                'appointment': cats.get('appointment', 0),
                'sales': cats.get('sale', 0),
                'spend': spend if self._can_view_spend() else None,
                'currency': currency,
                'cpl': self._safe_div(spend, count) if self._can_view_spend() else None,
                'drill_key': 'campaign',
                'drill_value': real_camp_id or False,
            })
        rows.sort(key=lambda r: r['leads'], reverse=True)
        return rows

    @api.model
    def _build_salespeople(self, filters, cohort_ids, called_ids, answered_ids, category_by_lead):
        domain = self._build_cohort_domain(filters)
        groups = self.env['crm.lead'].read_group(
            domain,
            ['user_id'],
            ['user_id'],
            lazy=False,
        )
        rows = []
        for g in groups:
            user = g.get('user_id')
            name = user[1] if user else _('Atanmamış')
            uid = user[0] if user else False
            count = g.get('user_id_count', 0)
            sub_domain = list(domain)
            if uid:
                sub_domain.append(('user_id', '=', uid))
            else:
                sub_domain.append(('user_id', '=', False))
            subset_ids = set(self.env['crm.lead'].search(sub_domain).ids)
            called = len(subset_ids & called_ids)
            reached = len(subset_ids & answered_ids)
            cats = defaultdict(int)
            for lid in subset_ids:
                cat = category_by_lead.get(lid)
                if cat:
                    cats[cat] += 1
            rows.append({
                'user_id': uid,
                'name': name,
                'leads': count,
                'called': called,
                'call_rate': self._pct(called, count),
                'reached': reached,
                'positive': cats.get('positive', 0),
                'appointment': cats.get('appointment', 0),
                'qualified': cats.get('qualified', 0),
                'sales': cats.get('sale', 0),
                'conversion': self._pct(cats.get('sale', 0), count),
                'drill_key': 'user',
                'drill_value': uid or False,
            })
        rows.sort(key=lambda r: r['leads'], reverse=True)
        return rows

    @api.model
    def _build_call_outcomes(self, category_counts, total):
        items = []
        for key, _label in CATEGORY_SELECTION:
            if key in ('reached', 'sale', 'lost'):
                continue
            count = category_counts.get(key, 0)
            if count:
                items.append({
                    'key': key,
                    'label': CATEGORY_LABELS.get(key, key),
                    'count': count,
                    'percent': self._pct(count, total),
                    'drill_key': 'category',
                    'drill_value': key,
                })
        return items

    @api.model
    def _build_table_rows(self, filters, source_rows, campaign_rows):
        """Merge source + campaign for analytical table."""
        rows = []
        for row in campaign_rows[:50]:
            rows.append({
                'kaynak': '—',
                'kampanya': row.get('campaign', '—'),
                'lead': row.get('leads', 0),
                'arandi': row.get('called', 0),
                'aranmadi': row.get('leads', 0) - row.get('called', 0),
                'olumlu': row.get('positive', 0),
                'randevu': row.get('appointment', 0),
                'satis': row.get('sales', 0),
                'harcama': row.get('spend'),
                'cpl': row.get('cpl'),
                'drill_key': row.get('drill_key'),
                'drill_value': row.get('drill_value'),
            })
        if not rows:
            for row in source_rows[:50]:
                rows.append({
                    'kaynak': row.get('source', '—'),
                    'kampanya': '—',
                    'lead': row.get('leads', 0),
                    'arandi': row.get('called', 0),
                    'aranmadi': row.get('uncalled', 0),
                    'olumlu': row.get('positive', 0),
                    'randevu': row.get('appointment', 0),
                    'satis': row.get('sales', 0),
                    'harcama': None,
                    'cpl': None,
                    'drill_key': row.get('drill_key'),
                    'drill_value': row.get('drill_value'),
                })
        return rows

    @api.model
    def _marketing_freshness(self):
        if not self._can_view_spend():
            return None
        if 'tcrm.marketing.daily.metric' not in self.env:
            return None
        Metric = self.env['tcrm.marketing.daily.metric']
        rec = Metric.search([
            ('company_id', '=', self._company().id),
        ], order='last_sync_at desc', limit=1)
        if not rec:
            return {'last_sync_at': False, 'stale': True, 'message': _('Pazarlama verisi henüz senkronize edilmedi.')}
        stale = False
        if rec.last_sync_at:
            age = fields.Datetime.now() - rec.last_sync_at
            stale = age > timedelta(hours=6)
        return {
            'last_sync_at': fields.Datetime.to_string(rec.last_sync_at) if rec.last_sync_at else False,
            'stale': stale,
            'sync_status': rec.sync_status,
            'message': format_datetime(self.env, rec.last_sync_at) if rec.last_sync_at else '',
        }

    @api.model
    def _cost_kpis(self, filters, cohort_ids, called_ids, answered_ids, category_counts):
        if not self._can_view_spend():
            return {}
        total_leads = len(cohort_ids)
        spend_total = 0.0
        currency = False
        if 'tcrm.marketing.daily.metric' in self.env:
            spend_total, currency = self.env['tcrm.marketing.daily.metric']._spend_total(
                self._company().id,
                filters.get('date_from'),
                filters.get('date_to'),
            )
        positive = category_counts.get('positive', 0)
        appointment = category_counts.get('appointment', 0)
        qualified = category_counts.get('qualified', 0)
        sales = category_counts.get('sale', 0)
        called_count = len(called_ids)
        reached_count = len(answered_ids)
        revenue = sum(
            self.env['crm.lead'].browse(list(cohort_ids)).filtered(
                lambda l: l.won_status == 'won'
            ).mapped('expected_revenue')
        )
        return {
            'spend_total': spend_total,
            'currency': currency or self._company().currency_id.name,
            'cpl': self._safe_div(spend_total, total_leads),
            'cost_per_called': self._safe_div(spend_total, called_count),
            'cost_per_reached': self._safe_div(spend_total, reached_count),
            'cost_per_positive': self._safe_div(spend_total, positive),
            'cost_per_appointment': self._safe_div(spend_total, appointment),
            'cost_per_qualified': self._safe_div(spend_total, qualified),
            'cost_per_sale': self._safe_div(spend_total, sales),
            'roas': self._safe_div(revenue, spend_total) if spend_total else None,
            'revenue': revenue,
        }

    # ------------------------------------------------------------------ public API
    @api.model
    def get_filter_options(self):
        company = self._company()
        sources = self.env['utm.source'].search([])
        users = self.env['res.users'].search([('share', '=', False)])
        teams = self.env['crm.team'].search([])
        stages = self.env['crm.stage'].search([])
        tags = self.env['crm.tag'].search([])
        campaigns = []
        if 'tcrm.marketing.meta.lead' in self.env:
            meta_groups = self.env['tcrm.marketing.meta.lead'].read_group(
                [('company_id', 'in', self.env.companies.ids), ('campaign_id_remote', '!=', False)],
                ['campaign_id_remote', 'campaign_name'],
                ['campaign_id_remote', 'campaign_name'],
                lazy=False,
            )
            seen = set()
            for g in meta_groups:
                cid = g.get('campaign_id_remote')
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                campaigns.append({
                    'id': cid,
                    'name': g.get('campaign_name') or cid,
                })
        if not campaigns and 'tcrm.marketing.campaign' in self.env:
            for camp in self.env['tcrm.marketing.campaign'].search([
                ('company_id', 'in', self.env.companies.ids),
            ], limit=200):
                if camp.platform_campaign_id:
                    campaigns.append({
                        'id': camp.platform_campaign_id,
                        'name': camp.name,
                    })
        projects = []
        if 'propertio.project' in self.env:
            projects = [
                {'id': p.id, 'name': p.name}
                for p in self.env['propertio.project'].search([('company_id', '=', company.id)])
            ]
        return {
            'sources': [{'id': s.id, 'name': s.name} for s in sources],
            'users': [{'id': u.id, 'name': u.name} for u in users],
            'teams': [{'id': t.id, 'name': t.name} for t in teams],
            'stages': [{'id': s.id, 'name': s.name} for s in stages],
            'tags': [{'id': t.id, 'name': t.name} for t in tags],
            'campaigns': campaigns,
            'projects': projects,
            'categories': [
                {'key': k, 'label': CATEGORY_LABELS.get(k, k)}
                for k, _ in CATEGORY_SELECTION
            ],
            'can_view_spend': self._can_view_spend(),
            'can_sync_marketing': self._can_sync_marketing(),
        }

    @api.model
    def get_lead_report_data(self, filters=None):
        filters = dict(filters or {})
        cohort_domain = self._build_cohort_domain(filters)
        leads = self._cohort_leads(filters)
        cohort_ids = set(leads.ids)
        total = len(cohort_ids)

        called_ids = self._called_lead_ids(cohort_ids)
        answered_ids = self._answered_lead_ids(cohort_ids)
        uncalled_ids = cohort_ids - called_ids
        unreachable_ids = called_ids - answered_ids

        StatusMap = self.env['tcrm.lead.report.status.map']
        category_by_lead = StatusMap.classify_leads(leads, company_id=self._company().id)
        category_counts = StatusMap.count_by_category(leads, company_id=self._company().id)

        today_count = self._today_lead_count(cohort_domain)
        first_call = self._first_call_metrics(cohort_ids)

        kpis = [
            self._kpi('total', _('Toplam Lead'), total, total),
            self._kpi('today', _('Bugünkü Lead'), today_count, total),
            self._kpi('called', _('Aranan Lead'), len(called_ids), total),
            self._kpi('uncalled', _('Aranmayan Lead'), len(uncalled_ids), total),
            self._kpi('reached', _('Ulaşılan'), len(answered_ids), total),
            self._kpi('unreachable', _('Ulaşılamayan'), len(unreachable_ids), total),
            self._kpi('positive', _('Olumlu'), category_counts.get('positive', 0), total),
            self._kpi('negative', _('Olumsuz'), category_counts.get('negative', 0), total),
            self._kpi('appointment', _('Randevu Verildi'), category_counts.get('appointment', 0), total),
            self._kpi('pending', _('Değerlendirilecek'), category_counts.get('pending', 0), total),
            self._kpi('not_available', _('Müsait Değil'), category_counts.get('not_available', 0), total),
            self._kpi('not_interested', _('İlgilenmiyor'), category_counts.get('not_interested', 0), total),
            self._kpi('sale', _('Satış Yapıldı'), category_counts.get('sale', 0), total),
            self._kpi('lost', _('Lost'), category_counts.get('lost', 0), total),
            self._kpi('qualified', _('Qualified'), category_counts.get('qualified', 0), total),
        ]

        source_rows = self._build_sources(filters, cohort_ids, called_ids, category_by_lead)
        campaign_rows = self._build_campaigns(filters, cohort_ids, called_ids, category_by_lead)
        salespeople = self._build_salespeople(
            filters, cohort_ids, called_ids, answered_ids, category_by_lead
        )
        call_outcomes = self._build_call_outcomes(category_counts, total)
        timeline = self._build_timeline(filters, called_ids, category_counts)
        costs = self._cost_kpis(filters, cohort_ids, called_ids, answered_ids, category_counts)
        table_rows = self._build_table_rows(filters, source_rows, campaign_rows)

        return {
            'meta': {
                'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
                'total_leads': total,
                'empty': total == 0,
                'can_view_spend': self._can_view_spend(),
                'can_sync_marketing': self._can_sync_marketing(),
            },
            'filters_echo': filters,
            'kpis': kpis,
            'costs': costs,
            'sources': source_rows,
            'call_outcomes': call_outcomes,
            'called_vs_uncalled': [
                {'label': _('Arandı'), 'count': len(called_ids), 'key': 'called'},
                {'label': _('Aranmadı'), 'count': len(uncalled_ids), 'key': 'uncalled'},
            ],
            'timeline': timeline,
            'campaigns': campaign_rows,
            'salespeople': salespeople,
            'table': {
                'rows': table_rows,
                'total': len(table_rows),
            },
            'marketing_freshness': self._marketing_freshness(),
            'first_call': first_call,
        }

    @api.model
    def _drill_domain(self, drill_key, drill_value, filters):
        domain = self._build_cohort_domain(filters)
        cohort_ids = set(self._cohort_leads(filters).ids)

        if drill_key == 'total':
            return domain
        if drill_key == 'today':
            today = fields.Date.context_today(self)
            dt_start, dt_end = self._datetime_bounds(today, today)
            domain.extend([
                ('create_date', '>=', fields.Datetime.to_string(dt_start)),
                ('create_date', '<=', fields.Datetime.to_string(dt_end)),
            ])
            return domain
        if drill_key == 'called':
            ids = list(self._called_lead_ids(cohort_ids))
            return domain + [('id', 'in', ids or [0])]
        if drill_key == 'uncalled':
            ids = list(cohort_ids - self._called_lead_ids(cohort_ids))
            return domain + [('id', 'in', ids or [0])]
        if drill_key == 'reached':
            ids = list(self._answered_lead_ids(cohort_ids))
            return domain + [('id', 'in', ids or [0])]
        if drill_key == 'unreachable':
            called = self._called_lead_ids(cohort_ids)
            answered = self._answered_lead_ids(cohort_ids)
            ids = list(called - answered)
            return domain + [('id', 'in', ids or [0])]
        if drill_key == 'source':
            if drill_value:
                return domain + [('source_id', '=', int(drill_value))]
            return domain + [('source_id', '=', False)]
        if drill_key == 'campaign':
            if drill_value:
                meta_leads = self.env['tcrm.marketing.meta.lead'].search([
                    ('campaign_id_remote', '=', str(drill_value)),
                    ('crm_lead_id', '!=', False),
                ])
                ids = [i for i in meta_leads.mapped('crm_lead_id').ids if i in cohort_ids]
                return domain + [('id', 'in', ids or [0])]
            unknown_ids = [
                lid for lid in cohort_ids
                if not self.env['crm.lead'].browse(lid).mh_campaign_id_remote
            ]
            return domain + [('id', 'in', unknown_ids or [0])]
        if drill_key == 'user':
            if drill_value:
                return domain + [('user_id', '=', int(drill_value))]
            return domain + [('user_id', '=', False)]
        if drill_key == 'category':
            leads = self._cohort_leads(filters)
            classified = self.env['tcrm.lead.report.status.map'].classify_leads(
                leads, company_id=self._company().id
            )
            ids = [lid for lid, cat in classified.items() if cat == drill_value]
            return domain + [('id', 'in', ids or [0])]
        if drill_key in ('positive', 'negative', 'appointment', 'pending', 'not_available',
                         'not_interested', 'sale', 'lost', 'qualified'):
            return self._drill_domain('category', drill_key, filters)
        return domain

    @api.model
    def open_drilldown(self, drill_key, drill_value, filters=None):
        filters = dict(filters or {})
        domain = self._drill_domain(drill_key, drill_value, filters)
        action = self.env.ref('tcrm_propertio.action_lead_havuzu', raise_if_not_found=False)
        if action:
            result = action.read()[0]
            result['domain'] = domain
            result['target'] = 'current'
            return result
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lead Havuzu'),
            'res_model': 'crm.lead',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }

    @api.model
    def trigger_marketing_sync(self):
        if not self._can_sync_marketing():
            raise AccessError(_('Pazarlama senkronizasyonu için yetkiniz yok.'))
        if 'tcrm.marketing.daily.metric' not in self.env:
            raise UserError(_('Marketing Hub günlük metrik modülü yüklü değil.'))
        return self.env['tcrm.marketing.daily.metric'].sync_recent_metrics()

    @api.model
    def export_report(self, filters=None, export_format='csv'):
        data = self.get_lead_report_data(filters)
        rows = data.get('table', {}).get('rows', [])
        if export_format == 'csv':
            buf = io.StringIO()
            fieldnames = [
                'kaynak', 'kampanya', 'lead', 'arandi', 'aranmadi',
                'olumlu', 'randevu', 'satis', 'harcama', 'cpl',
            ]
            writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            content = buf.getvalue().encode('utf-8-sig')
            filename = 'lead_raporu.csv'
            mimetype = 'text/csv'
        else:
            try:
                import xlsxwriter
            except ImportError as exc:
                raise UserError(_('xlsxwriter yüklü değil.')) from exc
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            sheet = workbook.add_worksheet('Lead Raporu')
            headers = [
                'Kaynak', 'Kampanya', 'Lead', 'Arandı', 'Aranmadı',
                'Olumlu', 'Randevu', 'Satış', 'Harcama', 'CPL',
            ]
            for col, h in enumerate(headers):
                sheet.write(0, col, h)
            for row_idx, row in enumerate(rows, start=1):
                sheet.write(row_idx, 0, row.get('kaynak', ''))
                sheet.write(row_idx, 1, row.get('kampanya', ''))
                sheet.write(row_idx, 2, row.get('lead', 0))
                sheet.write(row_idx, 3, row.get('arandi', 0))
                sheet.write(row_idx, 4, row.get('aranmadi', row.get('lead', 0) - row.get('arandi', 0)))
                sheet.write(row_idx, 5, row.get('olumlu', 0))
                sheet.write(row_idx, 6, row.get('randevu', 0))
                sheet.write(row_idx, 7, row.get('satis', 0))
                sheet.write(row_idx, 8, row.get('harcama') or '')
                sheet.write(row_idx, 9, row.get('cpl') or '')
            workbook.close()
            content = output.getvalue()
            filename = 'lead_raporu.xlsx'
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        return {
            'filename': filename,
            'mimetype': mimetype,
            'content': base64.b64encode(content).decode('ascii'),
        }
