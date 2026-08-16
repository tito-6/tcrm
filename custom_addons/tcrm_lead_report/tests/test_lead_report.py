# -*- coding: utf-8 -*-
"""Tests for Lead Raporu dashboard aggregation."""
from __future__ import annotations

from datetime import datetime, timedelta

try:
    from tcrm.tests import TransactionCase, tagged
except ImportError:
    from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'lead_report')
class TestLeadReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Report = cls.env['tcrm.lead.report']
        cls.Lead = cls.env['crm.lead']
        cls.Call = cls.env['tcrm.call.record']
        cls.company = cls.env.company
        cls.user = cls.env.user
        cls.team = cls.env['crm.team'].search([], limit=1) or cls.env['crm.team'].create({
            'name': 'Lead Report Test Team',
        })
        cls.source_meta = cls.env['utm.source'].create({'name': 'Test Meta Source'})
        cls.tag_positive = cls.env.ref('tcrm_propertio.crm_tag_olumlu', raise_if_not_found=False)
        if not cls.tag_positive:
            cls.tag_positive = cls.env['crm.tag'].create({'name': 'Olumlu'})
        cls.today = datetime.now().date()
        cls.date_from = (cls.today - timedelta(days=30)).isoformat()
        cls.date_to = cls.today.isoformat()

    def _create_lead(self, name, **kwargs):
        vals = {
            'name': name,
            'type': 'opportunity',
            'user_id': self.user.id,
            'team_id': self.team.id,
            'source_id': self.source_meta.id,
            'company_id': self.company.id,
        }
        vals.update(kwargs)
        return self.Lead.create(vals)

    def _filters(self, **extra):
        base = {'date_from': self.date_from, 'date_to': self.date_to}
        base.update(extra)
        return base

    def test_total_leads_in_range(self):
        before = self.Report.get_lead_report_data(self._filters())
        total_before = before['meta']['total_leads']
        self._create_lead('LR Test Lead A')
        self._create_lead('LR Test Lead B')
        data = self.Report.get_lead_report_data(self._filters())
        self.assertGreaterEqual(data['meta']['total_leads'], total_before + 2)

    def test_source_grouping(self):
        lead = self._create_lead('LR Source Test')
        data = self.Report.get_lead_report_data(self._filters())
        sources = {s['source']: s for s in data['sources']}
        self.assertIn(self.source_meta.name, sources)
        self.assertGreaterEqual(sources[self.source_meta.name]['leads'], 1)

    def test_called_uncalled(self):
        lead_called = self._create_lead('LR Called Lead', call_follow_up_state='called')
        lead_uncalled = self._create_lead('LR Uncalled Lead', call_follow_up_state='not_called')
        data = self.Report.get_lead_report_data(self._filters())
        kpi_map = {k['key']: k['count'] for k in data['kpis']}
        self.assertGreaterEqual(kpi_map.get('called', 0), 1)
        self.assertGreaterEqual(kpi_map.get('uncalled', 0), 1)
        action = self.Report.open_drilldown('uncalled', False, self._filters())
        self.assertEqual(action['res_model'], 'crm.lead')
        domain = action.get('domain') or []
        self.assertTrue(any(isinstance(d, (list, tuple)) and d[0] == 'id' for d in domain))

    def test_positive_tag_classification(self):
        lead = self._create_lead('LR Positive Lead', tag_ids=[(6, 0, [self.tag_positive.id])])
        data = self.Report.get_lead_report_data(self._filters())
        kpi_map = {k['key']: k['count'] for k in data['kpis']}
        self.assertGreaterEqual(kpi_map.get('positive', 0), 1)

    def test_salesperson_filter(self):
        lead = self._create_lead('LR User Filter Lead')
        data = self.Report.get_lead_report_data(self._filters(user_id=self.user.id))
        self.assertGreaterEqual(data['meta']['total_leads'], 1)
        for sp in data['salespeople']:
            if sp['user_id'] == self.user.id:
                self.assertGreaterEqual(sp['leads'], 1)
                break

    def test_empty_date_range(self):
        future = (self.today + timedelta(days=365)).isoformat()
        data = self.Report.get_lead_report_data({
            'date_from': future,
            'date_to': future,
        })
        self.assertTrue(data['meta']['empty'])
        self.assertEqual(data['meta']['total_leads'], 0)

    def test_drilldown_domain_total(self):
        action = self.Report.open_drilldown('total', False, self._filters())
        self.assertEqual(action['res_model'], 'crm.lead')

    def test_export_csv(self):
        self._create_lead('LR Export Lead')
        result = self.Report.export_report(self._filters(), 'csv')
        self.assertEqual(result['filename'], 'lead_raporu.csv')
        self.assertTrue(result['content'])

    def test_cpl_with_zero_leads(self):
        if 'tcrm.marketing.daily.metric' not in self.env:
            self.skipTest('Marketing daily metric not installed')
        Metric = self.env['tcrm.marketing.daily.metric']
        Metric._upsert_metric({
            'company_id': self.company.id,
            'level': 'campaign',
            'platform': 'meta',
            'platform_campaign_id': 'camp_test_999',
            'platform_adset_id': '',
            'platform_ad_id': '',
            'entity_name': 'Test Campaign',
            'metric_date': self.today,
            'spend': 100.0,
            'currency': 'TRY',
        })
        future = (self.today + timedelta(days=400)).isoformat()
        data = self.Report.with_user(
            self.env.ref('base.group_system').users[0]
            if self.env.ref('base.group_system').users
            else self.user
        ).get_lead_report_data({'date_from': future, 'date_to': future})
        if data.get('costs'):
            self.assertIsNone(data['costs'].get('cpl'))
