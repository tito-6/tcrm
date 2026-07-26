# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from tcrm.exceptions import UserError
from tcrm.tests import tagged

from ..services.dial_token import issue_dial_token, validate_dial_token
from .common import SantralCommon


@tagged('tcrm_call_center', 'post_install', '-at_install')
class TestTokenAndDial(SantralCommon):
    def test_prepare_outbound_and_dial_token(self):
        call, dial_token, config = self.env['tcrm.call.record'].with_user(self.user_a).with_company(self.company_a).action_prepare_outbound(
            res_model='crm.lead', res_id=self.lead_a.id,
        )
        self.assertEqual(call.destination_number, '+905551234567')
        self.assertEqual(call.caller_id, '+905551112233')
        self.assertTrue(validate_dial_token(
            self.env, dial_token, call_id=call.id, destination=call.destination_number, user_id=self.user_a.id,
        ))
        self.assertFalse(validate_dial_token(
            self.env, dial_token, call_id=call.id, destination='+905559999999', user_id=self.user_a.id,
        ))

    def test_destination_immutable_after_auth(self):
        call, dial_token, _c = self.env['tcrm.call.record'].with_user(self.user_a).with_company(self.company_a).action_prepare_outbound(
            res_model='crm.lead', res_id=self.lead_a.id,
        )
        call.sudo().write({'dial_token_used': True})
        with self.assertRaises(UserError):
            call.with_user(self.user_a).write({'destination_number': '+905559998877'})

    def test_reject_arbitrary_caller_id_from_vals(self):
        call, _t, _c = self.env['tcrm.call.record'].with_user(self.user_a).with_company(self.company_a).action_prepare_outbound(
            res_model='crm.lead', res_id=self.lead_a.id,
        )
        # Caller ID always comes from tenant config at prepare time.
        self.assertEqual(call.caller_id, self.config_a.verified_caller_id)

    def test_access_token_generation_mocked(self):
        from ..services.providers.twilio_provider import TwilioCallProvider

        provider = TwilioCallProvider(self.env, self.config_a)
        fake_token = MagicMock()
        fake_token.to_jwt.return_value = 'jwt-test-token'
        
        fake_client = MagicMock()
        fake_client.tokens.create.return_value = MagicMock(ice_servers=[{'url': 'stun:global.stun.twilio.com:3478'}])
        
        with patch.object(provider, '_client', return_value=fake_client), \
             patch('tcrm.addons.tcrm_call_center.services.providers.twilio_provider.AccessToken', return_value=fake_token), \
             patch('tcrm.addons.tcrm_call_center.services.providers.twilio_provider.VoiceGrant', return_value=MagicMock()):
            data = provider.create_access_token(identity='tcrm_test_u1', ttl_seconds=300)
            
        self.assertEqual(data['token'], 'jwt-test-token')
        self.assertIn('ice_servers', data)
        self.assertEqual(data['ice_servers'][0]['url'], 'stun:global.stun.twilio.com:3478')
        self.assertNotIn('auth_token', data)
        self.assertNotIn('api_key_secret', data)

    def test_crm_access_required(self):
        other_lead = self.env['crm.lead'].sudo().create({
            'name': 'Hidden Lead',
            'type': 'lead',
            'phone': '+905551111111',
            'company_id': self.company_b.id,
            'user_id': self.user_b.id,
        })
        with self.assertRaises(Exception):
            self.env['tcrm.call.record'].with_user(self.user_a).with_company(self.company_a).action_prepare_outbound(
                res_model='crm.lead', res_id=other_lead.id,
            )
