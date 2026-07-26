# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Assert key Propertio / CRM UI labels resolve to Turkish under lang=tr_TR."""
from tcrm.tests.common import TransactionCase


class TestTurkishTranslations(TransactionCase):

    def _tr(self, record):
        return record.with_context(lang='tr_TR')

    def test_01_lead_havuzu_menu_and_action_turkish(self):
        menu = self._tr(self.env.ref('tcrm_propertio.menu_lead_havuzu'))
        action = self._tr(self.env.ref('tcrm_propertio.action_lead_havuzu'))
        self.assertEqual(menu.name, 'Lead Havuzu')
        self.assertEqual(action.name, 'Lead Havuzu')

    def test_02_inventory_menu_is_proje_stok_ve_takibi(self):
        menu = self._tr(self.env.ref('tcrm_propertio.menu_propertio_inventory'))
        self.assertIn(menu.name.lower(), ('proje stok ve takibi',))
        self.assertNotEqual(menu.name, 'Envanter')
        self.assertNotEqual(menu.name, 'Inventory')

    def test_03_create_reminder_field_string_turkish(self):
        field = self.env['mail.activity.schedule']._fields['create_reminder']
        # Source string is already Turkish; tr_TR must keep / resolve it.
        self.assertEqual(field.string, 'Hatırlatıcı oluştur')
        # Translated field get via fields_get under tr_TR
        info = self.env['mail.activity.schedule'].with_context(lang='tr_TR').fields_get(
            ['create_reminder'],
        )
        self.assertEqual(info['create_reminder']['string'], 'Hatırlatıcı oluştur')

    def test_04_crm_bridge_field_labels_turkish(self):
        info = self.env['crm.lead'].with_context(lang='tr_TR').fields_get(
            ['propertio_project_id', 'propertio_unit_id', 'propertio_sale_ids'],
        )
        self.assertEqual(info['propertio_project_id']['string'], 'Gayrimenkul Projesi')
        self.assertEqual(info['propertio_unit_id']['string'], 'Gayrimenkul Birimi')
        self.assertEqual(info['propertio_sale_ids']['string'], 'Gayrimenkul Sözleşmeleri')

    def test_05_project_amenities_labels_turkish(self):
        info = self.env['propertio.project'].with_context(lang='tr_TR').fields_get(
            ['name', 'block_ids', 'standard_feature_ids', 'extra_feature_ids'],
        )
        self.assertEqual(info['name']['string'], 'Proje Adı')
        self.assertEqual(info['block_ids']['string'], 'Bloklar')
        self.assertEqual(info['standard_feature_ids']['string'], 'Standart Olanaklar')
        self.assertEqual(info['extra_feature_ids']['string'], 'Mevcut Yükseltmeler')

    def test_06_havuzu_search_view_filter_strings_turkish(self):
        view = self.env.ref('tcrm_propertio.view_crm_lead_havuzu_search')
        arch = view.arch_db or view.arch
        for expected in (
            'Yeni Leadler',
            'Nitelikli Leadler',
            'Fırsatlar',
            'Satış Yapıldı',
            'Kaybedildi',
            'Arşivlendi',
            'Leadlerim',
            'Atanmamış',
            'Oluşturma Tarihi',
            'Satış Danışmanı',
            'Satış Ekibi',
        ):
            self.assertIn(expected, arch, 'Missing Turkish filter label: %s' % expected)
        for english in (
            'New Leads',
            'Qualified Leads',
            'My Leads',
            'Unassigned',
            'Creation Date',
            'Salesperson',
            'Sales Team',
        ):
            self.assertNotIn(english, arch, 'English leftover still present: %s' % english)
