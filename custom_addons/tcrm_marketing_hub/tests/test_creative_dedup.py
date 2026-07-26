# -*- coding: utf-8 -*-
from tcrm import fields
from tcrm.exceptions import ValidationError
from tcrm.tests import tagged
from tcrm.tools import mute_logger

from .common import MarketingHubCommon


@tagged('tcrm_marketing_hub', 'post_install', '-at_install')
class TestCreativeDedup(MarketingHubCommon):

    def test_creative_dedup_by_platform_ad_id(self):
        MetaAd = self.env['tcrm.marketing.meta.ad']
        first = MetaAd.create({
            'name': 'Kreatif A',
            'platform_ad_id': 'pad_unique_1',
            'company_id': self.company.id,
            'source_platform': 'instagram',
            'creative_json': '{"imageUrl": "https://example.com/a.jpg", "body": "Merhaba"}',
            'last_sync_at': fields.Datetime.now(),
        })
        raised = False
        with mute_logger('tcrm.sql_db'):
            try:
                with self.env.cr.savepoint():
                    MetaAd.create({
                        'name': 'Kreatif B',
                        'platform_ad_id': 'pad_unique_1',
                        'company_id': self.company.id,
                    })
            except (ValidationError, Exception):
                raised = True
        self.assertTrue(raised, 'Duplicate platform_ad_id must raise')
        existing = MetaAd.search([('platform_ad_id', '=', 'pad_unique_1')], limit=1)
        self.assertEqual(existing, first)
        self.assertEqual(
            MetaAd.search_count([('platform_ad_id', '=', 'pad_unique_1')]),
            1,
        )
        existing.write({
            'name': 'Kreatif A Güncel',
            'creative_json': '{"videoId": "v1", "thumbnailUrl": "https://example.com/t.jpg"}',
        })
        preview = existing.get_creative_preview()
        self.assertEqual(preview['media_type'], 'video')
        self.assertTrue(preview['thumbnail_url'])

    def test_missing_media_handled_gracefully(self):
        MetaAd = self.env['tcrm.marketing.meta.ad']
        ad = MetaAd.create({
            'name': 'Boş Kreatif',
            'platform_ad_id': 'pad_empty_1',
            'company_id': self.company.id,
            'creative_json': '{}',
        })
        preview = ad.get_creative_preview()
        self.assertEqual(preview['media_type'], 'none')
        self.assertFalse(preview['image_url'])

        form = self._make_form(self.account_enabled, 'form_creative', 'Kreatif Form')
        meta = self._make_meta_lead(
            form,
            leadgen_id='lg_creative_1',
            ad_id='pad_empty_1',
            ad_name='Boş Kreatif',
            campaign_name='Kampanya X',
        )
        # Computed creative_html should not crash; empty-state message expected
        self.assertTrue(meta.creative_html)
        self.assertIn('Kreatif önizleme yok', meta.creative_html)
        self.assertEqual(meta.ad_name, 'Boş Kreatif')
        self.assertEqual(meta.campaign_name, 'Kampanya X')
