# -*- coding: utf-8 -*-
from unittest.mock import patch

from tcrm.tests import tagged

from ..services.providers.twilio_provider import TwilioCallProvider
from .common import SantralCommon


@tagged('tcrm_call_center', 'post_install', '-at_install')
class TestTwimlWebhooks(SantralCommon):
    def test_twiml_recording_enabled(self):
        provider = TwilioCallProvider(self.env, self.config_a)
        call = self.env['tcrm.call.record'].sudo().create({
            'company_id': self.company_a.id,
            'user_id': self.user_a.id,
            'destination_number': '+905551234567',
            'caller_id': '+905551112233',
        })
        xml = provider.build_outgoing_twiml(
            to_number=call.destination_number,
            from_number=self.config_a.verified_caller_id,
            call_record=call,
            status_callback='https://tcrm.online/tcrm/twilio/call/status',
            recording_callback='https://tcrm.online/tcrm/twilio/recording/status',
        )
        self.assertIn('<Dial', xml)
        self.assertIn('callerId="+905551112233"', xml)
        self.assertIn('record-from-answer-dual', xml)
        self.assertIn('+905551234567', xml)
        self.assertIn('Say', xml)

    def test_twiml_recording_disabled(self):
        self.config_a.with_user(self.admin_a).write({
            'recording_enabled': False,
            'recording_announcement_enabled': False,
        })
        provider = TwilioCallProvider(self.env, self.config_a)
        call = self.env['tcrm.call.record'].sudo().create({
            'company_id': self.company_a.id,
            'user_id': self.user_a.id,
            'destination_number': '+905551234567',
        })
        xml = provider.build_outgoing_twiml(
            to_number=call.destination_number,
            from_number=self.config_a.verified_caller_id,
            call_record=call,
            status_callback='https://tcrm.online/tcrm/twilio/call/status',
            recording_callback='https://tcrm.online/tcrm/twilio/recording/status',
        )
        self.assertNotIn('record=', xml)
        self.assertNotIn('<Say', xml)

    def test_signature_validation(self):
        provider = TwilioCallProvider(self.env, self.config_a)
        with patch.object(provider, '_auth_token', return_value='test-auth-token-value'):
            with patch('tcrm.addons.tcrm_call_center.services.providers.twilio_provider.RequestValidator') as RV:
                RV.return_value.validate.return_value = True
                self.assertTrue(provider.validate_webhook_signature(
                    'https://tcrm.online/tcrm/twilio/call/status', {'CallSid': 'CA1'}, 'sig',
                ))
                RV.return_value.validate.return_value = False
                self.assertFalse(provider.validate_webhook_signature(
                    'https://tcrm.online/tcrm/twilio/call/status', {'CallSid': 'CA1'}, 'bad',
                ))

    def test_duplicate_webhook_fingerprint(self):
        Event = self.env['tcrm.call.webhook.event']
        e1, dup1 = Event.register_or_skip(
            company=self.company_a,
            call=self.env['tcrm.call.record'],
            event_type='call_status',
            provider_sid='CAxxxxxxxx',
            status='ringing',
            timestamp='t1',
            safe_payload={'CallStatus': 'ringing'},
        )
        e2, dup2 = Event.register_or_skip(
            company=self.company_a,
            call=self.env['tcrm.call.record'],
            event_type='call_status',
            provider_sid='CAxxxxxxxx',
            status='ringing',
            timestamp='t1',
            safe_payload={'CallStatus': 'ringing'},
        )
        self.assertFalse(dup1)
        self.assertTrue(dup2)
        self.assertEqual(e1.id, e2.id)

    def test_status_transitions(self):
        call = self.env['tcrm.call.record'].sudo().create({
            'company_id': self.company_a.id,
            'user_id': self.user_a.id,
            'destination_number': '+905551234567',
            'status': 'pending',
        })
        call._apply_status_event(call_status='initiated', call_sid='CA_parent')
        self.assertEqual(call.status, 'initiated')
        
        # Child leg ringing
        call._apply_status_event(call_status='ringing', call_sid='CA_child', parent_sid='CA_parent')
        self.assertEqual(call.status, 'ringing')
        self.assertTrue(call.ringing_time)
        self.assertEqual(call.child_call_sid, 'CA_child')
        self.assertEqual(call.provider_call_sid, 'CA_parent')
        
        # Child leg fails
        call._apply_status_event(call_status='failed', call_sid='CA_child', parent_sid='CA_parent', error_code='31005')
        self.assertEqual(call.status, 'failed')
        self.assertEqual(call.provider_error_code, '31005')
        
        # Parent leg drops (hangup from child failing)
        call._apply_status_event(call_status='completed', call_sid='CA_parent')
        # Ensure status is STILL failed
        self.assertEqual(call.status, 'failed')
        
        # Test no-answer flow
        call2 = self.env['tcrm.call.record'].sudo().create({
            'company_id': self.company_a.id,
            'user_id': self.user_a.id,
            'destination_number': '+905551234567',
            'status': 'pending',
        })
        call2._apply_status_event(call_status='initiated', call_sid='CA_parent_2')
        call2._apply_status_event(call_status='ringing', call_sid='CA_child_2', parent_sid='CA_parent_2')
        call2._apply_status_event(call_status='no-answer', call_sid='CA_child_2', parent_sid='CA_parent_2')
        self.assertEqual(call2.status, 'no-answer')
        # Parent drops
        call2._apply_status_event(call_status='completed', call_sid='CA_parent_2')
        self.assertEqual(call2.status, 'no-answer')
        
        # Test completed flow
        call3 = self.env['tcrm.call.record'].sudo().create({
            'company_id': self.company_a.id,
            'user_id': self.user_a.id,
            'destination_number': '+905551234567',
            'status': 'pending',
        })
        call3._apply_status_event(call_status='initiated', call_sid='CA_parent_3')
        call3._apply_status_event(call_status='ringing', call_sid='CA_child_3', parent_sid='CA_parent_3')
        call3._apply_status_event(call_status='in-progress', call_sid='CA_child_3', parent_sid='CA_parent_3')
        self.assertEqual(call3.status, 'in-progress')
        call3._apply_status_event(call_status='completed', call_sid='CA_child_3', parent_sid='CA_parent_3')
        self.assertEqual(call3.status, 'completed')
        call3._apply_status_event(call_status='completed', call_sid='CA_parent_3')
        self.assertEqual(call3.status, 'completed')
        
        # Ensure user error message is mapped
        self.assertIn('Twilio, Türkiye aramalarında Türk caller', call.user_error_message)
