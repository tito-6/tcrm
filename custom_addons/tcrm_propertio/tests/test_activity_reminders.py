# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Tests for CRM activity automatic calendar + To-Do reminders."""
from datetime import date, timedelta

from tcrm.tests.common import TransactionCase


class TestActivityReminders(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Reminder Contact'})
        cls.lead = cls.env['crm.lead'].create({
            'name': 'Reminder Lead Opp',
            'type': 'opportunity',
            'partner_id': cls.partner.id,
            'user_id': cls.env.user.id,
        })
        cls.activity_type = cls.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not cls.activity_type:
            cls.activity_type = cls.env['mail.activity.type'].create({
                'name': 'Custom Follow-up',
                'category': 'default',
            })
        cls.deadline = date.today() + timedelta(days=3)

    def _schedule(self, create_reminder=True, summary='Call back'):
        wizard = self.env['mail.activity.schedule'].with_context(
            active_model='crm.lead',
            active_id=self.lead.id,
            active_ids=[self.lead.id],
        ).create({
            'res_model': 'crm.lead',
            'res_ids': str([self.lead.id]),
            'activity_type_id': self.activity_type.id,
            'summary': summary,
            'note': '<p>Please follow up</p>',
            'date_deadline': self.deadline,
            'activity_user_id': self.env.user.id,
            'create_reminder': create_reminder,
        })
        return wizard._action_schedule_activities()

    def test_01_reminder_creates_calendar_and_todo(self):
        activities = self._schedule()
        self.assertEqual(len(activities), 1)
        activity = activities[0]
        self.assertTrue(activity.todo_task_id, 'To-Do task must be linked')
        self.assertTrue(
            activity.reminder_calendar_event_id or activity.calendar_event_id,
            'Calendar event must be linked',
        )
        event = activity._tcrm_reminder_calendar_event()
        self.assertIn(self.lead.display_name, event.name)
        self.assertIn(self.activity_type.name, event.name)
        if 'opportunity_id' in event._fields:
            self.assertEqual(event.opportunity_id, self.lead)
        attendee_partners = event.attendee_ids.mapped('partner_id') | event.partner_ids
        self.assertIn(
            self.env.user.partner_id, attendee_partners,
            'Responsible user must be an event attendee',
        )
        todo = activity.todo_task_id
        self.assertIn(self.lead.display_name, todo.name)
        self.assertIn(self.env.user, todo.user_ids)
        desc = str(todo.description or '')
        self.assertTrue(
            'CRM Link' in desc or 'CRM Bağlantısı' in desc or 'CRM Baglantisi' in desc,
            desc,
        )
        self.assertIn('crm.lead', desc)

    def test_02_deduplication_updates_existing(self):
        activities = self._schedule(summary='First')
        activity = activities[0]
        todo_id = activity.todo_task_id.id
        event_id = activity._tcrm_reminder_calendar_event().id
        activity.write({'summary': 'Updated summary'})
        activity._tcrm_sync_reminders()
        activity.invalidate_recordset()
        self.assertEqual(activity.todo_task_id.id, todo_id)
        self.assertEqual(activity._tcrm_reminder_calendar_event().id, event_id)
        self.assertEqual(
            self.env['project.task'].search_count([
                ('id', '=', todo_id),
            ]),
            1,
        )
        self.assertEqual(
            self.env['calendar.event'].search_count([
                ('id', '=', event_id),
                ('active', '=', True),
            ]),
            1,
        )

    def test_03_done_marks_todo_and_cancels_calendar(self):
        activity = self._schedule()[0]
        todo = activity.todo_task_id
        event = activity._tcrm_reminder_calendar_event()
        activity.action_feedback(feedback='Done')
        self.assertEqual(todo.state, '1_done')
        self.assertFalse(event.active)

    def test_04_unlink_cancels_reminders(self):
        activity = self._schedule()[0]
        todo = activity.todo_task_id
        event = activity._tcrm_reminder_calendar_event()
        activity.unlink()
        self.assertEqual(todo.state, '1_canceled')
        self.assertFalse(event.active)

    def test_05_no_reminder_when_unchecked(self):
        activities = self._schedule(create_reminder=False)
        activity = activities[0]
        self.assertFalse(activity.todo_task_id)
        self.assertFalse(activity.reminder_calendar_event_id)

    def test_06_preference_persisted(self):
        wizard = self.env['mail.activity.schedule'].with_context(
            active_model='crm.lead',
            active_id=self.lead.id,
            active_ids=[self.lead.id],
        ).create({
            'res_model': 'crm.lead',
            'res_ids': str([self.lead.id]),
            'activity_type_id': self.activity_type.id,
            'date_deadline': self.deadline,
            'activity_user_id': self.env.user.id,
            'create_reminder': False,
        })
        wizard._action_schedule_activities()
        self.assertFalse(
            self.env['mail.activity.schedule']._tcrm_get_create_reminder_pref(default=True)
        )
