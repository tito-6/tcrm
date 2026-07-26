# -*- coding: utf-8 -*-
from tcrm.exceptions import AccessError
from tcrm.tests import tagged

from ..services.crypto import decrypt_secret, encrypt_secret
from .common import SantralCommon


@tagged('tcrm_call_center', 'post_install', '-at_install')
class TestCryptoSettings(SantralCommon):
    def test_secret_encrypted_at_rest(self):
        stored = self.config_a.sudo().api_key_secret_encrypted
        self.assertTrue(stored.startswith('enc:v1:'))
        self.assertNotIn('test-api-secret-value', stored)
        plain = decrypt_secret(self.env, stored)
        self.assertEqual(plain, 'test-api-secret-value')

    def test_secret_masked_in_read(self):
        row = self.config_a.with_user(self.admin_a).read([
            'api_key_secret', 'auth_token', 'api_key_secret_encrypted', 'auth_token_encrypted',
        ])[0]
        self.assertEqual(row['api_key_secret'], '********')
        self.assertEqual(row['auth_token'], '********')
        self.assertTrue(row['api_key_secret_encrypted'] in (True, 1))
        self.assertTrue(row['auth_token_encrypted'] in (True, 1))

    def test_ordinary_user_cannot_edit_settings(self):
        with self.assertRaises(AccessError):
            self.config_a.with_user(self.user_a).write({'enabled': False})

    def test_no_global_fallback_when_disabled(self):
        self.config_a.with_user(self.admin_a).write({'enabled': False})
        cfg = self.env['tcrm.call.provider.config'].with_company(self.company_a).get_for_company(
            self.company_a, require_enabled=True,
        )
        self.assertFalse(cfg)

    def test_encrypt_roundtrip(self):
        enc = encrypt_secret(self.env, 'abc123')
        self.assertEqual(decrypt_secret(self.env, enc), 'abc123')
