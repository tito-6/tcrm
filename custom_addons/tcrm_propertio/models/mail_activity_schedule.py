# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Schedule wizard: optional automatic calendar + To-Do reminder for CRM leads."""
from tcrm import api, fields, models


REMINDER_PREF_KEY = 'tcrm_propertio.activity_create_reminder'


class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    create_reminder = fields.Boolean(
        string='Hatırlatıcı oluştur',
        help='CRM lead aktivitesi planlanırken takvim etkinliği ve kişisel Yapılacak oluştur.',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'create_reminder' in fields_list or not fields_list:
            res_model = res.get('res_model') or self.env.context.get('active_model')
            # Default True for crm.lead; otherwise still use remembered preference (default True)
            res['create_reminder'] = self._tcrm_get_create_reminder_pref(default=True)
            if res_model and res_model != 'crm.lead':
                # Keep preference value but reminders only apply to crm.lead on schedule
                pass
        return res

    @api.model
    def _tcrm_get_create_reminder_pref(self, default=True):
        ICP = self.env['ir.config_parameter'].sudo()
        # Per-user preference; fall back to global key then default
        user_key = '%s.%s' % (REMINDER_PREF_KEY, self.env.uid)
        val = ICP.get_param(user_key)
        if val in (None, False, ''):
            val = ICP.get_param(REMINDER_PREF_KEY)
        if val in (None, False, ''):
            return default
        return str(val).lower() in ('1', 'true', 'yes')

    def _tcrm_save_create_reminder_pref(self):
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        user_key = '%s.%s' % (REMINDER_PREF_KEY, self.env.uid)
        ICP.set_param(user_key, 'True' if self.create_reminder else 'False')
        # Also keep the shared key updated as last-used default
        ICP.set_param(REMINDER_PREF_KEY, 'True' if self.create_reminder else 'False')

    def _action_schedule_activities(self):
        activities = super()._action_schedule_activities()
        self._tcrm_save_create_reminder_pref()
        if self.create_reminder and self.res_model == 'crm.lead' and activities:
            activities._tcrm_sync_reminders()
        return activities

    def action_schedule_plan(self):
        before_ids = set()
        records = self._get_applied_on_records() if self.res_model == 'crm.lead' else self.env['crm.lead']
        if self.create_reminder and self.res_model == 'crm.lead' and records:
            before_ids = set(self.env['mail.activity'].search([
                ('res_model', '=', 'crm.lead'),
                ('res_id', 'in', records.ids),
            ]).ids)
        result = super().action_schedule_plan()
        self._tcrm_save_create_reminder_pref()
        if self.create_reminder and self.res_model == 'crm.lead' and records:
            new_activities = self.env['mail.activity'].search([
                ('res_model', '=', 'crm.lead'),
                ('res_id', 'in', records.ids),
                ('id', 'not in', list(before_ids) or [0]),
                ('active', '=', True),
            ])
            if new_activities:
                new_activities._tcrm_sync_reminders()
        return result

    def action_create_calendar_event(self):
        """Calendar meeting path: still create To-Do reminder when requested."""
        result = super().action_create_calendar_event()
        self._tcrm_save_create_reminder_pref()
        if self.create_reminder and (self.res_model == 'crm.lead' or self.env.context.get('active_model') == 'crm.lead'):
            res_ids = self._evaluate_res_ids()
            if res_ids:
                activities = self.env['mail.activity'].search([
                    ('res_model', '=', 'crm.lead'),
                    ('res_id', 'in', res_ids),
                    ('active', '=', True),
                ], order='id desc', limit=max(1, len(res_ids)))
                # Sync todos; calendar is handled by the meeting wizard
                for activity in activities:
                    lead = self.env['crm.lead'].browse(activity.res_id).exists()
                    if lead:
                        activity._tcrm_sync_todo_reminder(lead)
        return result
