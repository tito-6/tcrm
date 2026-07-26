# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Verify Propertio report category numbering is continuous 1..N."""
from tcrm.addons.tcrm_propertio.models.propertio_report_center import (
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    REPORT_CATALOG,
)
from tcrm.tests.common import TransactionCase


class TestReportNumbering(TransactionCase):

    def test_category_order_covers_labels(self):
        self.assertEqual(
            set(CATEGORY_ORDER),
            set(CATEGORY_LABELS.keys()),
            'CATEGORY_ORDER must list every CATEGORY_LABELS key',
        )

    def test_category_numbers_continuous_no_skips_or_repeats(self):
        engine = self.env['propertio.report.engine']
        numbers = engine._category_number_map()
        present = {item['category'] for item in REPORT_CATALOG}
        self.assertEqual(set(numbers.keys()), present)

        values = sorted(numbers.values())
        self.assertEqual(values, list(range(1, len(values) + 1)))
        self.assertEqual(len(values), len(set(values)), 'category numbers must be unique')

        ordered_present = [c for c in CATEGORY_ORDER if c in present]
        for idx, cat in enumerate(ordered_present, start=1):
            self.assertEqual(numbers[cat], idx)

    def test_list_reports_exposes_numbered_category_labels(self):
        catalog = self.env['propertio.report.engine'].list_reports()
        reports = catalog['reports']
        self.assertTrue(reports)
        seen = {}
        for report in reports:
            self.assertIn('category_number', report)
            self.assertIn('category_label', report)
            n = report['category_number']
            self.assertIsInstance(n, int)
            self.assertGreaterEqual(n, 1)
            label = report['category_label']
            self.assertTrue(label.startswith('%s. ' % n), label)
            if report['category'] in seen:
                self.assertEqual(seen[report['category']], n)
            else:
                seen[report['category']] = n
        values = sorted(seen.values())
        self.assertEqual(values, list(range(1, len(values) + 1)))

    def test_menu_category_names_are_numbered_sequentially(self):
        expected = [
            ('tcrm_propertio.menu_report_category_collection', '1. Tahsilat ve Ödemeler'),
            ('tcrm_propertio.menu_report_category_sales', '2. Satış Raporları'),
            ('tcrm_propertio.menu_report_category_customer', '3. Müşteri Raporları'),
            ('tcrm_propertio.menu_report_category_finance', '4. Mali Raporlar'),
            ('tcrm_propertio.menu_report_category_performance', '5. Performans Raporları'),
            ('tcrm_propertio.menu_report_category_property', '6. Gayrimenkul Raporları'),
            ('tcrm_propertio.menu_report_category_admin', '7. Yönetim ve Uyum'),
            ('tcrm_propertio.menu_report_category_marketing', '8. Pazarlama ve Müşteri Adayları'),
        ]
        for xmlid, name in expected:
            menu = self.env.ref(xmlid)
            self.assertEqual(menu.name, name)
