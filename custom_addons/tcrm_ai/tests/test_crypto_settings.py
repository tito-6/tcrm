# Part of TCRM AI. See LICENSE for details.

from tcrm.tests import tagged, TransactionCase

from ..services.crypto import decrypt_secret, encrypt_secret, mask_api_key
from ..services.constants import DEFAULT_GROQ_MODEL


@tagged('tcrm_ai', 'post_install', '-at_install')
class TestTcrmAiCryptoSettings(TransactionCase):

    def setUp(self):
        super().setUp()
        self.config = self.env['tcrm.ai.config'].get_config()

    def test_encrypt_roundtrip(self):
        enc = encrypt_secret(self.env, 'gsk_test_secret_key_value_1234')
        self.assertTrue(enc.startswith('enc:v1:'))
        self.assertEqual(decrypt_secret(self.env, enc), 'gsk_test_secret_key_value_1234')

    def test_key_encrypted_at_rest(self):
        self.config.write({'api_key_input': 'gsk_abcdefghijklmnopqrstuvwxyz1234'})
        stored = self.config.sudo().api_key_encrypted
        self.assertTrue(stored.startswith('enc:v1:'))
        self.assertNotIn('gsk_abcdefghijklmnopqrstuvwxyz1234', stored)

    def test_key_masking(self):
        masked = mask_api_key('gsk_abcdefghijklmnopqrstuvwxyz1234')
        self.assertTrue(masked.startswith('gsk_'))
        self.assertTrue(masked.endswith('1234'))
        self.assertNotIn('abcdefgh', masked)

    def test_key_not_returned_by_rpc_read(self):
        self.config.write({'api_key_input': 'gsk_abcdefghijklmnopqrstuvwxyz1234'})
        row = self.config.read(['api_key_encrypted', 'api_key_masked', 'has_api_key'])[0]
        self.assertIn(row['api_key_encrypted'], (True, 1))
        self.assertTrue(row['has_api_key'])
        self.assertTrue(str(row['api_key_masked']).endswith('1234'))
        self.assertNotIn('abcdefghijklmnopqrstuvwxyz', str(row['api_key_masked']))

    def test_allowed_model_validation(self):
        self.config.write({'model': DEFAULT_GROQ_MODEL})
        self.assertEqual(self.config.model, DEFAULT_GROQ_MODEL)

    def test_disallowed_model_rejection(self):
        with self.assertRaises(Exception):
            self.config.write({'model': 'gpt-4o-arbitrary'})

    def test_tenant_local_configuration(self):
        self.assertEqual(self.config.company_id, self.env.company)
        self.assertEqual(self.config._get_plaintext_api_key() or '', decrypt_secret(self.env, self.config.api_key_encrypted))

    def test_changing_model_keeps_key(self):
        self.config.write({'api_key_input': 'gsk_keep_this_key_value_9999'})
        key_before = self.config._get_plaintext_api_key()
        self.config.write({'model': DEFAULT_GROQ_MODEL})
        self.assertEqual(self.config._get_plaintext_api_key(), key_before)
