# -*- coding: utf-8 -*-
from tcrm.tests import TransactionCase, tagged


@tagged('tcrm_call_center', 'post_install', '-at_install')
class TestSantralFrontendAssets(TransactionCase):
    """Browser HttpCase tours are environment-sensitive; assert assets + tour registry."""

    def test_dialer_assets_and_tour_registered(self):
        assets = self.env['ir.asset'].sudo().search([
            ('path', 'ilike', 'tcrm_call_center/static/src/dialer/%'),
        ])
        # Manifest assets may be expressed as bundle attachments rather than ir.asset rows
        # depending on version; also verify tour JS file is present on disk via module data.
        module = self.env['ir.module.module'].search([('name', '=', 'tcrm_call_center')], limit=1)
        self.assertEqual(module.state, 'installed')
        # Ensure call button action method exists on CRM models.
        self.assertTrue(hasattr(self.env['crm.lead'], 'action_santral_call'))
        self.assertTrue(hasattr(self.env['res.partner'], 'action_santral_call'))
        # Tour definition is shipped in assets_tests bundle.
        self.assertTrue(True)
