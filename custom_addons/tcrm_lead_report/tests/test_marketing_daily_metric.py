# -*- coding: utf-8 -*-
"""Tests for marketing daily metric upsert/idempotency."""
from __future__ import annotations

try:
    from tcrm.tests import TransactionCase, tagged
except ImportError:
    from odoo.tests import TransactionCase, tagged

from tcrm import fields

@tagged('post_install', '-at_install', 'lead_report', 'marketing_daily_metric')
class TestMarketingDailyMetric(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'tcrm.marketing.daily.metric' not in cls.env:
            cls.skipTest('tcrm.marketing.daily.metric not installed')
        cls.Metric = cls.env['tcrm.marketing.daily.metric']
        cls.company = cls.env.company
        cls.today = fields.Date.context_today(cls.env['tcrm.marketing.daily.metric'])

    def test_upsert_idempotent(self):
        vals = {
            'company_id': self.company.id,
            'level': 'campaign',
            'platform': 'meta',
            'platform_campaign_id': 'idempotent_camp_1',
            'platform_adset_id': '',
            'platform_ad_id': '',
            'entity_name': 'Idempotent Campaign',
            'metric_date': self.today,
            'spend': 50.0,
            'currency': 'TRY',
        }
        rec1 = self.Metric._upsert_metric(dict(vals))
        vals['spend'] = 75.0
        rec2 = self.Metric._upsert_metric(dict(vals))
        self.assertEqual(rec1.id, rec2.id)
        self.assertEqual(rec2.spend, 75.0)
        count = self.Metric.search_count([
            ('company_id', '=', self.company.id),
            ('platform_campaign_id', '=', 'idempotent_camp_1'),
            ('metric_date', '=', self.today),
        ])
        self.assertEqual(count, 1)

    def test_spend_total(self):
        self.Metric._upsert_metric({
            'company_id': self.company.id,
            'level': 'campaign',
            'platform': 'meta',
            'platform_campaign_id': 'spend_total_camp',
            'platform_adset_id': '',
            'platform_ad_id': '',
            'entity_name': 'Spend Total Camp',
            'metric_date': self.today,
            'spend': 200.0,
            'currency': 'TRY',
        })
        total, currency = self.Metric._spend_total(
            self.company.id,
            self.today.isoformat(),
            self.today.isoformat(),
        )
        self.assertGreaterEqual(total, 200.0)
        self.assertEqual(currency, 'TRY')

    def test_company_isolation(self):
        other_company = self.env['res.company'].create({'name': 'Other LR Test Co'})
        self.Metric._upsert_metric({
            'company_id': other_company.id,
            'level': 'campaign',
            'platform': 'meta',
            'platform_campaign_id': 'other_co_camp',
            'platform_adset_id': '',
            'platform_ad_id': '',
            'entity_name': 'Other Co',
            'metric_date': self.today,
            'spend': 999.0,
            'currency': 'TRY',
        })
        total, _currency = self.Metric.with_company(self.company)._spend_total(
            self.company.id,
            self.today.isoformat(),
            self.today.isoformat(),
        )
        records = self.Metric.with_company(self.company).search([
            ('company_id', '=', other_company.id),
            ('platform_campaign_id', '=', 'other_co_camp'),
        ])
        self.assertFalse(records)
