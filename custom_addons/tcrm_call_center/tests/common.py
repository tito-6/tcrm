# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from tcrm.tests import TransactionCase, tagged

from ..services.crypto import encrypt_secret


@tagged('tcrm_call_center')
class SantralCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env['res.company'].create({'name': 'Santral Tenant A'})
        cls.company_b = cls.env['res.company'].create({'name': 'Santral Tenant B'})
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.admin_a = Users.create({
            'name': 'Santral Admin A',
            'login': 'santral_admin_a_%s' % cls.company_a.id,
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('tcrm_call_center.group_santral_admin').id,
                cls.env.ref('tcrm_call_center.group_santral_recording_listen').id,
                cls.env.ref('tcrm_call_center.group_santral_recording_download').id,
                cls.env.ref('sales_team.group_sale_salesman_all_leads').id,
            ])],
        })
        cls.user_a = Users.create({
            'name': 'Santral User A',
            'login': 'santral_user_a_%s' % cls.company_a.id,
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('tcrm_call_center.group_santral_user').id,
                cls.env.ref('sales_team.group_sale_salesman').id,
            ])],
        })
        cls.user_b = Users.create({
            'name': 'Santral User B',
            'login': 'santral_user_b_%s' % cls.company_b.id,
            'company_id': cls.company_b.id,
            'company_ids': [(6, 0, [cls.company_b.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('tcrm_call_center.group_santral_user').id,
                cls.env.ref('sales_team.group_sale_salesman').id,
            ])],
        })
        cls.listener_a = Users.create({
            'name': 'Santral Listener A',
            'login': 'santral_listener_a_%s' % cls.company_a.id,
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('tcrm_call_center.group_santral_user').id,
                cls.env.ref('tcrm_call_center.group_santral_recording_listen').id,
                cls.env.ref('sales_team.group_sale_salesman_all_leads').id,
            ])],
        })
        Config = cls.env['tcrm.call.provider.config'].sudo()
        cls.config_a = Config.search([('company_id', '=', cls.company_a.id)], limit=1)
        if not cls.config_a:
            cls.config_a = Config.create({'company_id': cls.company_a.id, 'provider': 'twilio'})
        cls.config_b = Config.search([('company_id', '=', cls.company_b.id)], limit=1)
        if not cls.config_b:
            cls.config_b = Config.create({'company_id': cls.company_b.id, 'provider': 'twilio'})

        cls.config_a.with_user(cls.admin_a).write({
            'account_sid': 'ACaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            'api_key_sid': 'SKbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
            'api_key_secret': 'test-api-secret-value',
            'auth_token': 'test-auth-token-value',
            'twiml_app_sid': 'APcccccccccccccccccccccccccccccccc',
            'verified_caller_id': '+905551112233',
            'public_callback_base_url': 'https://tcrm.online',
            'recording_enabled': True,
            'dual_channel_recording': True,
            'recording_announcement_enabled': True,
            'enabled': True,
        })

        Partner = cls.env['res.partner'].with_company(cls.company_a)
        cls.partner_a = Partner.create({
            'name': 'Santral Contact A',
            'phone': '+905551234567',
            'company_id': cls.company_a.id,
        })
        cls.lead_a = cls.env['crm.lead'].with_user(cls.user_a).with_company(cls.company_a).create({
            'name': 'Santral Lead A',
            'type': 'opportunity',
            'partner_id': cls.partner_a.id,
            'phone': '+905551234567',
            'user_id': cls.user_a.id,
            'company_id': cls.company_a.id,
        })

    def _mock_twilio_token(self):
        return patch(
            'tcrm.addons.tcrm_call_center.services.providers.twilio_provider.AccessToken',
            return_value=MagicMock(**{
                'add_grant': MagicMock(),
                'to_jwt': MagicMock(return_value='jwt-test-token'),
            }),
        )
