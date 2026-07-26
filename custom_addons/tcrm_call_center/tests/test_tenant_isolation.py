# -*- coding: utf-8 -*-
from tcrm.tests import tagged

from .common import SantralCommon


@tagged('tcrm_call_center', 'post_install', '-at_install')
class TestTenantIsolation(SantralCommon):
    def test_company_b_cannot_see_company_a_calls(self):
        call = self.env['tcrm.call.record'].sudo().create({
            'company_id': self.company_a.id,
            'user_id': self.user_a.id,
            'destination_number': '+905551234567',
        })
        found = self.env['tcrm.call.record'].with_user(self.user_b).with_company(self.company_b).search([
            ('id', '=', call.id),
        ])
        self.assertFalse(found)

    def test_company_b_cannot_see_company_a_config_secrets(self):
        rows = self.config_a.with_user(self.user_b).with_company(self.company_b).search([
            ('id', '=', self.config_a.id),
        ])
        self.assertFalse(rows)

    def test_owner_config_not_copied_to_other_tenant(self):
        # config_b must remain empty/disabled and not inherit secrets
        self.assertFalse(self.config_b.enabled)
        self.assertFalse(self.config_b.api_key_secret_encrypted)
        self.assertFalse(self.config_b.auth_token_encrypted)
        self.assertNotEqual(self.config_b.account_sid, self.config_a.account_sid)

    def test_no_global_fallback(self):
        self.config_b.sudo().write({'enabled': False, 'account_sid': False})
        cfg = self.env['tcrm.call.provider.config'].with_company(self.company_b).get_for_company(
            self.company_b, require_enabled=True,
        )
        self.assertFalse(cfg)

    def test_master_safe_status_has_no_secrets(self):
        status = self.config_a.master_safe_status()
        blob = str(status)
        self.assertNotIn('test-api-secret-value', blob)
        self.assertNotIn('test-auth-token-value', blob)
        self.assertIn('account_sid_masked', status)
