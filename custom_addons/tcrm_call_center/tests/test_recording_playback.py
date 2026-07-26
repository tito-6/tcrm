# -*- coding: utf-8 -*-
from tcrm.exceptions import AccessError, UserError
from tcrm.tests import tagged

from .common import SantralCommon


@tagged('tcrm_call_center', 'post_install', '-at_install')
class TestRecordingPlayback(SantralCommon):
    def _make_recording(self):
        call = self.env['tcrm.call.record'].sudo().create({
            'company_id': self.company_a.id,
            'user_id': self.user_a.id,
            'lead_id': self.lead_a.id,
            'destination_number': '+905551234567',
            'status': 'completed',
            'recording_state': 'ready',
            'provider_call_sid': 'CArec1',
        })
        rec = self.env['tcrm.call.recording'].sudo().create({
            'company_id': self.company_a.id,
            'call_id': call.id,
            'recording_sid': 'REaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            'status': 'completed',
            'duration': 12,
            'channels': 2,
        })
        return call, rec

    def test_playback_requires_permission(self):
        _call, rec = self._make_recording()
        with self.assertRaises(AccessError):
            rec.with_user(self.user_a)._check_playback_access()
        rec.with_user(self.listener_a)._check_playback_access()

    def test_download_requires_separate_permission(self):
        _call, rec = self._make_recording()
        self.config_a.with_user(self.admin_a).write({'allow_recording_download': True})
        with self.assertRaises(AccessError):
            rec.with_user(self.listener_a)._check_download_access()
        rec.with_user(self.admin_a)._check_download_access()

    def test_retention_purge(self):
        _call, rec = self._make_recording()
        rec.sudo().write({'retention_deadline': '2000-01-01'})
        self.env['tcrm.call.recording'].cron_purge_expired()
        self.assertEqual(rec.status, 'deleted')

    def test_recording_linkage(self):
        call, rec = self._make_recording()
        self.assertEqual(rec.lead_id, self.lead_a)
        self.assertEqual(call.recording_ids, rec)
