# Part of TCRM AI Research. See LICENSE for details.

from tcrm.tests import tagged

from ..services.context_builder import ContextBuilder
from .common import AiResearchCommon


@tagged('tcrm_ai_research', 'post_install', '-at_install')
class TestContextBuilder(AiResearchCommon):

    def test_builds_turkish_lead_context(self):
        self.lead.description = 'Müşteri İstanbul ofisi için teklif istedi — ğüşıöç'
        ctx = ContextBuilder(self.env(user=self.user_ai)).build(lead_id=self.lead.id)
        self.assertEqual(ctx['lead_id'], self.lead.id)
        self.assertIn('Fırsat Örnek', ctx['prompt_text'])
        self.assertIn('ğüşıöç', ctx['prompt_text'])

    def test_omits_missing_records(self):
        ctx = ContextBuilder(self.env(user=self.user_ai)).build(lead_id=99999999)
        self.assertFalse(ctx.get('lead'))
