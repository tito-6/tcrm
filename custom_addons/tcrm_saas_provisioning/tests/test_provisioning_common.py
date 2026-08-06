# -*- coding: utf-8 -*-
"""Pure-logic tests for provisioning helpers (no DB / no side effects)."""
from tcrm.tests.common import TransactionCase
from tcrm.addons.tcrm_saas_provisioning.models import provisioning_common as pc


class TestProvisioningCommon(TransactionCase):

    def test_valid_db_names(self):
        for good in ('acme', 'acme_estates', 'nova_estates_2026', 'a1_b2_c3'):
            self.assertTrue(pc.is_valid_db_name(good), good)

    def test_invalid_db_names(self):
        for bad in ('', 'Acme', 'acme-estates', 'a', 'ab', '1acme', 'acme.db',
                    'acme db', 'acme;drop', 'a' * 64, None, 123):
            self.assertFalse(pc.is_valid_db_name(bad), repr(bad))

    def test_reserved_db_names_rejected(self):
        for r in ('postgres', 'template0', 'template1', 'tcrm_master', 'master'):
            self.assertFalse(pc.is_valid_db_name(r), r)
            with self.assertRaises(ValueError):
                pc.validate_db_name(r)

    def test_validate_db_name_raises_on_hyphen(self):
        with self.assertRaises(ValueError):
            pc.validate_db_name('acme-estates')

    def test_parse_module_set_ok(self):
        self.assertEqual(
            pc.parse_module_set('base, web ,crm,base'),  # dedup + order preserved
            ['base', 'web', 'crm'])

    def test_parse_module_set_rejects_bad_token(self):
        for bad in ('base,web;rm -rf', 'base,--stop', 'base,web mod!', ''):
            with self.assertRaises(ValueError):
                pc.parse_module_set(bad)

    def test_sign_and_verify(self):
        secret = 'super-secret'
        tok = pc.sign_job(secret, 42, 'acme', 'nonce123')
        self.assertTrue(pc.verify_job(secret, tok, 42, 'acme', 'nonce123'))
        # Any tampering invalidates.
        self.assertFalse(pc.verify_job(secret, tok, 43, 'acme', 'nonce123'))
        self.assertFalse(pc.verify_job(secret, tok, 42, 'other', 'nonce123'))
        self.assertFalse(pc.verify_job(secret, tok, 42, 'acme', 'nonceXXX'))
        self.assertFalse(pc.verify_job('wrong-secret', tok, 42, 'acme', 'nonce123'))
        self.assertFalse(pc.verify_job(secret, '', 42, 'acme', 'nonce123'))
