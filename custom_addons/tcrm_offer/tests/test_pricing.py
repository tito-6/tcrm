# -*- coding: utf-8 -*-
from tcrm.tests import tagged, TransactionCase

from ..services.pricing import (
    meta_ad_management_fee_kurus,
    meta_requires_custom_fee,
    to_kurus,
    apply_tax,
    quote_offer,
    validate_exclusive_groups,
)


@tagged('post_install', '-at_install', 'tcrm_offer')
class TestOfferPricing(TransactionCase):

    def test_meta_budget_boundaries(self):
        from decimal import Decimal
        cases = [
            (50_000, 30_000),
        ]
        for budget, expected_major in cases:
            fee = meta_ad_management_fee_kurus(to_kurus(budget))
            self.assertEqual(fee, to_kurus(expected_major), msg=f'budget={budget}')

        # percentage tiers — compare via same domain function expectations
        self.assertEqual(
            meta_ad_management_fee_kurus(to_kurus(50_001)),
            to_kurus(Decimal('50001') * Decimal('0.35')),
        )
        self.assertEqual(
            meta_ad_management_fee_kurus(to_kurus(69_999)),
            to_kurus(Decimal('69999') * Decimal('0.35')),
        )
        self.assertEqual(
            meta_ad_management_fee_kurus(to_kurus(70_000)),
            to_kurus(Decimal('70000') * Decimal('0.32')),
        )
        self.assertEqual(
            meta_ad_management_fee_kurus(to_kurus(99_999)),
            to_kurus(Decimal('99999') * Decimal('0.32')),
        )
        self.assertEqual(
            meta_ad_management_fee_kurus(to_kurus(100_000)),
            to_kurus(Decimal('100000') * Decimal('0.31')),
        )
        self.assertEqual(
            meta_ad_management_fee_kurus(to_kurus(500_000)),
            to_kurus(Decimal('500000') * Decimal('0.31')),
        )

        with self.assertRaises(ValueError):
            meta_ad_management_fee_kurus(to_kurus(500_001))

        self.assertTrue(meta_requires_custom_fee(to_kurus(500_001)))
        fee = meta_ad_management_fee_kurus(to_kurus(500_001), to_kurus(150_000))
        self.assertEqual(fee, to_kurus(150_000))

    def test_tax_and_periods(self):
        tax = apply_tax(to_kurus(20_000), 20)
        self.assertEqual(tax['net'], to_kurus(20_000))
        self.assertEqual(tax['tax'], to_kurus(4_000))
        self.assertEqual(tax['gross'], to_kurus(24_000))

        items = [
            {
                'id': 1, 'name': 'Meta', 'pricing_type': 'meta_budget',
                'unit_price_kurus': 0, 'billing_period': 'monthly',
                'required': True, 'taxable': True, 'exclusive_group': '',
            },
            {
                'id': 2, 'name': 'SM', 'pricing_type': 'fixed',
                'unit_price_kurus': to_kurus(20_000), 'billing_period': 'monthly',
                'required': False, 'taxable': True, 'exclusive_group': 'social_media',
            },
            {
                'id': 3, 'name': 'Photo', 'pricing_type': 'fixed',
                'unit_price_kurus': to_kurus(20_000), 'billing_period': 'per_session',
                'required': False, 'taxable': True, 'exclusive_group': '',
            },
        ]
        quote = quote_offer(
            items, {1, 2, 3},
            tax_rate_percent=20,
            ad_budget_kurus=to_kurus(50_000),
        )
        # 30k meta + 20k sm monthly; 20k session
        self.assertEqual(quote['monthly']['net'], to_kurus(50_000))
        self.assertEqual(quote['per_session']['net'], to_kurus(20_000))
        self.assertEqual(quote['net_kurus'], to_kurus(70_000))
        self.assertEqual(quote['tax_kurus'], to_kurus(14_000))
        self.assertEqual(quote['gross_kurus'], to_kurus(84_000))

    def test_exclusive_groups(self):
        with self.assertRaises(ValueError):
            validate_exclusive_groups([
                {'id': 1, 'exclusive_group': 'social_media'},
                {'id': 2, 'exclusive_group': 'social_media'},
            ])
        validate_exclusive_groups([
            {'id': 1, 'exclusive_group': 'social_media'},
            {'id': 2, 'exclusive_group': ''},
        ])
