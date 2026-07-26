# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from tcrm.exceptions import AccessError
from tcrm.tests import tagged

from .common import MarketingHubCommon


@tagged('tcrm_marketing_hub', 'post_install', '-at_install')
class TestPageSelection(MarketingHubCommon):

    def _assert_payload_has_no_secrets(self, payload):
        forbidden_keys = {
            'api_key', 'apikey', 'api-key', 'token', 'access_token',
            'authorization', 'bearer', 'secret', 'password',
        }

        def walk(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    self.assertNotIn(
                        str(key).lower(),
                        forbidden_keys,
                        'Secret key leaked in payload: %s' % key,
                    )
                    walk(value)
            elif isinstance(obj, (list, tuple)):
                for item in obj:
                    walk(item)

        walk(payload)

    def test_sync_forms_skips_disabled_accounts(self):
        called_ids = []

        def fake_list_lead_forms(account_id=None, limit=50):
            called_ids.append(account_id)
            return {'forms': [{
                'id': 'remote_form_%s' % account_id,
                'name': 'Form %s' % account_id,
                'status': 'ACTIVE',
                'leads_count': 0,
                'questions': [],
            }]}

        client = MagicMock()
        client.list_lead_forms.side_effect = fake_list_lead_forms

        with patch.object(
            type(self.env['tcrm.marketing.profile']),
            '_get_zernio_client',
            return_value=client,
        ):
            self.env['tcrm.marketing.lead.form'].action_sync_from_zernio()

        self.assertIn(self.account_enabled.zernio_id, called_ids)
        self.assertNotIn(self.account_disabled.zernio_id, called_ids)
        self.assertNotIn(self.other_account.zernio_id, called_ids)

        Form = self.env['tcrm.marketing.lead.form']
        self.assertTrue(Form.search([
            ('account_id', '=', self.account_enabled.id),
        ]))
        self.assertFalse(Form.search([
            ('account_id', '=', self.account_disabled.id),
        ]))

    def test_sync_all_forms_respects_sync_enabled(self):
        form_on = self._make_form(self.account_enabled, 'form_on', 'On Form')
        form_off = self._make_form(self.account_disabled, 'form_off', 'Off Form')
        synced = []

        def fake_sync_leads(self_form, *, limit_pages=5, import_crm=True):
            synced.append(self_form.id)
            return 0

        with patch.object(
            type(self.env['tcrm.marketing.lead.form']),
            'action_sync_from_zernio',
            return_value=0,
        ), patch.object(
            type(self.env['tcrm.marketing.lead.form']),
            'action_sync_leads',
            fake_sync_leads,
        ):
            self.env['tcrm.marketing.meta.lead'].action_sync_all_forms()

        self.assertIn(form_on.id, synced)
        self.assertNotIn(form_off.id, synced)

    def test_disable_page_keeps_existing_leads(self):
        form = self._make_form(self.account_enabled)
        meta = self._make_meta_lead(form, leadgen_id='lg_keep_1')
        Hub = self.env['tcrm.marketing.hub'].with_user(self.user_manager)
        Hub.action_disable_page(self.account_enabled.id)
        self.assertFalse(self.account_enabled.sync_enabled)
        self.assertTrue(self.account_enabled.disabled_at)
        self.assertTrue(meta.exists())
        self.assertEqual(meta.form_id.account_id, self.account_enabled)

    def test_get_page_management_no_tokens(self):
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('tcrm_marketing_hub.zernio_api_key', 'SUPER_SECRET_API_KEY_XYZ')
        data = self.env['tcrm.marketing.hub'].with_user(self.user_marketing).get_page_management()
        dumped = str(data)
        self.assertNotIn('SUPER_SECRET_API_KEY_XYZ', dumped)
        self._assert_payload_has_no_secrets(data)
        if data.get('profile'):
            self.assertIn('name', data['profile'])
            self.assertIn('zernio_id', data['profile'])
            self.assertNotIn('api_key', data['profile'])
        account_ids = {a['id'] for a in data['accounts']}
        self.assertIn(self.account_enabled.id, account_ids)
        self.assertIn(self.account_disabled.id, account_ids)
        self.assertNotIn(self.other_account.id, account_ids)

    def test_test_connection_no_tokens(self):
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('tcrm_marketing_hub.zernio_api_key', 'SECRET_TOKEN_VALUE_99')

        client = MagicMock()
        client.list_profiles.return_value = [{
            '_id': 'p1',
            'name': 'Profil A',
            'apiKey': 'SHOULD_NOT_LEAK',
            'token': 'SHOULD_NOT_LEAK_EITHER',
        }]

        with patch.object(
            type(self.env['tcrm.marketing.profile']),
            '_get_zernio_client',
            return_value=client,
        ):
            result = self.env['tcrm.marketing.hub'].with_user(
                self.user_manager
            ).action_test_connection()

        self.assertTrue(result['success'])
        dumped = str(result)
        self.assertNotIn('SECRET_TOKEN_VALUE_99', dumped)
        self.assertNotIn('SHOULD_NOT_LEAK', dumped)
        self._assert_payload_has_no_secrets(result)

    def test_company_isolation_for_accounts(self):
        data = self.env['tcrm.marketing.hub'].get_page_management()
        ids = {a['id'] for a in data['accounts']}
        self.assertIn(self.account_enabled.id, ids)
        self.assertNotIn(self.other_account.id, ids)

        other_env = self.env['tcrm.marketing.hub'].with_company(self.other_company)
        other_data = other_env.get_page_management()
        other_ids = {a['id'] for a in other_data['accounts']}
        self.assertIn(self.other_account.id, other_ids)
        self.assertNotIn(self.account_enabled.id, other_ids)

    def test_user_cannot_set_page_selection(self):
        Hub = self.env['tcrm.marketing.hub'].with_user(self.user_marketing)
        with self.assertRaises(AccessError):
            Hub.set_page_selection([self.account_enabled.id])

    def test_manager_can_set_page_selection(self):
        Hub = self.env['tcrm.marketing.hub'].with_user(self.user_manager)
        data = Hub.set_page_selection([self.account_disabled.id])
        self.account_enabled.invalidate_recordset()
        self.account_disabled.invalidate_recordset()
        self.assertFalse(self.account_enabled.sync_enabled)
        self.assertTrue(self.account_disabled.sync_enabled)
        enabled = [a for a in data['accounts'] if a['sync_enabled']]
        self.assertEqual({a['id'] for a in enabled}, {self.account_disabled.id})
