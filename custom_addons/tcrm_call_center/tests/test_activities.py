# -*- coding: utf-8 -*-
from tcrm.tests import tagged

from .common import SantralCommon


@tagged('tcrm_call_center', 'post_install', '-at_install')
class TestActivities(SantralCommon):
    def test_wrapup_creates_followup_once(self):
        call = self.env['tcrm.call.record'].with_user(self.user_a).with_company(self.company_a).create({
            'company_id': self.company_a.id,
            'user_id': self.user_a.id,
            'lead_id': self.lead_a.id,
            'destination_number': '+905551234567',
            'status': 'completed',
        })
        call.with_user(self.user_a).action_save_wrapup(
            outcome='callback',
            notes='Tekrar aranacak',
            create_followup=True,
            followup_summary='Santral takip',
        )
        self.assertTrue(call.followup_activity_id)
        first_id = call.followup_activity_id.id
        call.with_user(self.user_a).action_save_wrapup(
            outcome='callback',
            notes='Tekrar',
            create_followup=True,
        )
        self.assertEqual(call.followup_activity_id.id, first_id)
