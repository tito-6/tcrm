# -*- coding: utf-8 -*-
"""Configurable mapping from CRM tags / call outcomes to report categories."""
from __future__ import annotations

from tcrm import api, fields, models, _

try:
    from tcrm_call_center.models.call_record import OUTCOME_SELECTION
except ImportError:
    OUTCOME_SELECTION = [
        ('reached', 'Ulaşıldı'),
        ('not_reached', 'Ulaşılamadı'),
        ('busy', 'Meşgul'),
        ('no_answer', 'Cevapsız'),
        ('wrong_number', 'Yanlış Numara'),
        ('callback', 'Tekrar Aranacak'),
        ('appointment', 'Randevu Oluşturuldu'),
        ('interested', 'İlgileniyor'),
        ('not_interested', 'İlgilenmiyor'),
        ('opportunity', 'Satış Fırsatı Oluşturuldu'),
    ]

CATEGORY_SELECTION = [
    ('positive', 'Olumlu'),
    ('negative', 'Olumsuz'),
    ('unreachable', 'Ulaşılamadı'),
    ('not_available', 'Müsait Değil'),
    ('not_interested', 'İlgilenmiyor'),
    ('pending', 'Değerlendirilecek'),
    ('appointment', 'Randevu Verildi'),
    ('reached', 'Ulaşıldı'),
    ('qualified', 'Qualified'),
    ('sale', 'Satış Yapıldı'),
    ('lost', 'Lost'),
    ('hot', 'Sıcak Müşteri'),
]

CATEGORY_LABELS = dict(CATEGORY_SELECTION)

# Priority when a lead matches multiple categories (higher wins).
CATEGORY_PRIORITY = {
    'sale': 100,
    'appointment': 90,
    'positive': 80,
    'qualified': 75,
    'hot': 70,
    'reached': 65,
    'pending': 50,
    'not_available': 40,
    'not_interested': 35,
    'negative': 30,
    'unreachable': 25,
    'lost': 20,
}


class TcrmLeadReportStatusMap(models.Model):
    _name = 'tcrm.lead.report.status.map'
    _description = 'Lead Report Status Mapping'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Şirket',
        help='Boş bırakılırsa tüm şirketler için geçerlidir.',
    )
    category = fields.Selection(CATEGORY_SELECTION, required=True, index=True)
    tag_id = fields.Many2one('crm.tag', string='CRM Etiketi', ondelete='cascade')
    call_outcome = fields.Selection(
        selection=OUTCOME_SELECTION,
        string='Çağrı Sonucu',
    )
    note = fields.Text(string='Not')

    _sql_constraints = [
        (
            'tag_or_outcome_required',
            'CHECK(tag_id IS NOT NULL OR call_outcome IS NOT NULL)',
            'Etiket veya çağrı sonucu seçilmelidir.',
        ),
    ]

    @api.model
    def _mapping_cache(self, company_id=None):
        """Return {tag_id: category, outcome: category} for active mappings."""
        domain = [('active', '=', True)]
        if company_id:
            domain = ['|', ('company_id', '=', False), ('company_id', '=', company_id)] + domain[1:]
        tag_map = {}
        outcome_map = {}
        for rec in self.search(domain, order='sequence, id'):
            if rec.tag_id:
                tag_map[rec.tag_id.id] = rec.category
            if rec.call_outcome:
                outcome_map[rec.call_outcome] = rec.category
        return tag_map, outcome_map

    @api.model
    def classify_leads(self, leads, company_id=None):
        """Return dict lead_id -> category key (or False)."""
        if not leads:
            return {}
        tag_map, outcome_map = self._mapping_cache(company_id)
        Call = self.env['tcrm.call.record']
        lead_ids = leads.ids
        latest_outcome = {}
        if outcome_map and 'tcrm.call.record' in self.env:
            calls = Call.search([
                ('lead_id', 'in', lead_ids),
                ('outcome', '!=', False),
            ], order='id desc')
            for call in calls:
                lid = call.lead_id.id
                if lid not in latest_outcome:
                    latest_outcome[lid] = call.outcome

        result = {}
        for lead in leads:
            categories = []
            for tag in lead.tag_ids:
                cat = tag_map.get(tag.id)
                if cat:
                    categories.append(cat)
            outcome = latest_outcome.get(lead.id)
            if outcome and outcome in outcome_map:
                categories.append(outcome_map[outcome])
            if lead.won_status == 'won':
                categories.append('sale')
            elif lead.won_status == 'lost':
                categories.append('lost')
            if not categories:
                result[lead.id] = False
                continue
            result[lead.id] = max(categories, key=lambda c: CATEGORY_PRIORITY.get(c, 0))
        return result

    @api.model
    def count_by_category(self, leads, company_id=None):
        """Count leads per category key."""
        classified = self.classify_leads(leads, company_id=company_id)
        counts = {key: 0 for key, _label in CATEGORY_SELECTION}
        counts['unknown'] = 0
        for _lid, cat in classified.items():
            if cat and cat in counts:
                counts[cat] += 1
            else:
                counts['unknown'] += 1
        return counts
