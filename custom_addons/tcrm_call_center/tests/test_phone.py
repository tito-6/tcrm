# -*- coding: utf-8 -*-
from tcrm.exceptions import UserError
from tcrm.tests import tagged

from ..services.phone import assert_allowed_destination, mask_phone, normalize_e164
from .common import SantralCommon


@tagged('tcrm_call_center', 'post_install', '-at_install')
class TestPhone(SantralCommon):
    def test_e164_normalization_tr(self):
        self.assertEqual(normalize_e164('0555 123 4567'), '+905551234567')
        self.assertEqual(normalize_e164('5551234567'), '+905551234567')
        self.assertEqual(normalize_e164('+90 555 123 4567'), '+905551234567')

    def test_mask_phone(self):
        self.assertTrue(mask_phone('+905551234567').endswith('4567'))
        self.assertIn('*', mask_phone('+905551234567'))

    def test_reject_malformed(self):
        with self.assertRaises(UserError):
            normalize_e164('12')

    def test_reject_premium(self):
        with self.assertRaises(UserError):
            assert_allowed_destination('+19005551212')
