# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Ensure AI / PLS probability UI is hidden on CRM lead form inherits."""
from lxml import etree

from tcrm.tests.common import TransactionCase


class TestHideAiProbability(TransactionCase):

    def test_form_inherit_hides_ai_probability_ui(self):
        view = self.env.ref('tcrm_propertio.crm_lead_view_form_hide_ai_probability')
        self.assertEqual(view.model, 'crm.lead')
        self.assertEqual(
            view.inherit_id,
            self.env.ref('crm.crm_lead_view_form'),
        )
        arch = etree.fromstring(view.arch_db)
        xpath_nodes = arch.xpath('//xpath')
        self.assertTrue(xpath_nodes)
        expr = xpath_nodes[0].get('expr') or ''
        self.assertIn("probability", expr)
        self.assertEqual(xpath_nodes[0].get('position'), 'replace')

        # Combined form arch after inheritance must not expose AI probability UI
        combined = self.env['crm.lead'].get_view(view_id=self.env.ref('crm.crm_lead_view_form').id)
        combined_arch = etree.fromstring(combined['arch'])

        # AI controls removed from visible tree
        self.assertFalse(
            combined_arch.xpath("//*[@name='action_set_automated_probability']"),
            'AI probability switch must not remain in form arch',
        )
        self.assertFalse(
            combined_arch.xpath("//widget[@name='pls_tooltip_button']"),
            'PLS tooltip widget must not remain in form arch',
        )
        self.assertFalse(
            combined_arch.xpath("//label[@for='probability']"),
            'Visible probability label must be removed',
        )

        # Fields kept (invisible) for JS
        prob_fields = combined_arch.xpath("//field[@name='probability']")
        self.assertTrue(prob_fields, 'probability field must remain for JS')
        for field in prob_fields:
            self.assertEqual(field.get('invisible'), '1')
        auto_fields = combined_arch.xpath("//field[@name='automated_probability']")
        self.assertTrue(auto_fields, 'automated_probability field must remain for JS')
        for field in auto_fields:
            self.assertEqual(field.get('invisible'), '1')
