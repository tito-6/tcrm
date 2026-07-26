# -*- coding: utf-8 -*-
from tcrm import fields
from tcrm.tests import tagged

from .common import MarketingHubCommon


@tagged('tcrm_marketing_hub', 'post_install', '-at_install')
class TestCrmLeadSource(MarketingHubCommon):

    def test_crm_lead_source_fields_from_meta_lead(self):
        form = self._make_form(self.account_enabled, 'form_src_1', 'Kaynak Formu')
        form.last_sync_at = fields.Datetime.now()
        crm = self.env['crm.lead'].create({
            'name': '[Instagram] Test Lead',
            'type': 'lead',
            'company_id': self.company.id,
        })
        meta = self._make_meta_lead(
            form,
            leadgen_id='lg_crm_src_1',
            crm_lead_id=crm.id,
            source_platform='instagram',
            ad_id='ad_999',
            ad_name='IG Story Kreatif',
            campaign_name='Bahar Kampanyası',
            campaign_id_remote='camp_999',
            created_time=fields.Datetime.now(),
            state='imported',
        )
        crm.invalidate_recordset()
        self.assertTrue(crm.marketing_has_meta_lead)
        self.assertIn(meta, crm.marketing_meta_lead_ids)
        self.assertEqual(crm.mh_source_platform, 'Instagram')
        self.assertEqual(crm.mh_campaign_name, 'Bahar Kampanyası')
        self.assertEqual(crm.mh_campaign_id_remote, 'camp_999')
        self.assertEqual(crm.mh_ad_name, 'IG Story Kreatif')
        self.assertEqual(crm.mh_ad_id, 'ad_999')
        self.assertEqual(crm.mh_form_name, 'Kaynak Formu')
        self.assertEqual(crm.mh_form_zernio_id, 'form_src_1')
        self.assertEqual(crm.mh_page_zernio_id, self.account_enabled.zernio_id)
        self.assertEqual(crm.mh_profile_name, self.profile.name)
        self.assertEqual(crm.mh_leadgen_id, 'lg_crm_src_1')
        self.assertTrue(crm.mh_created_time)
        self.assertTrue(crm.mh_last_sync_at)
        self.assertTrue(crm.mh_sync_state)

    def test_crm_lead_empty_without_meta(self):
        crm = self.env['crm.lead'].create({
            'name': 'Plain Lead',
            'type': 'lead',
            'company_id': self.company.id,
        })
        self.assertFalse(crm.marketing_has_meta_lead)
        self.assertFalse(crm.mh_leadgen_id)
        self.assertFalse(crm.mh_creative_html)
