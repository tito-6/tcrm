# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""CRM activity reminders: calendar.event + project.task (personal To-Do) linkage."""
from datetime import datetime, time

from markupsafe import Markup, escape

from tcrm import api, fields, models, _
from tcrm.tools import html2plaintext, is_html_empty


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    todo_task_id = fields.Many2one(
        'project.task',
        string='Hatırlatıcı Yapılacak',
        index='btree_not_null',
        ondelete='set null',
        copy=False,
        help='Bu CRM aktivitesi için hatırlatıcı olarak oluşturulan kişisel Yapılacak.',
    )
    reminder_calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Hatırlatıcı Takvim Etkinliği',
        index='btree_not_null',
        ondelete='set null',
        copy=False,
        help='Hatırlatıcı olarak oluşturulan takvim etkinliği (varsa calendar_event_id kullanılır).',
    )

    def _tcrm_reminder_calendar_event(self):
        """Return the linked calendar event used for reminders."""
        self.ensure_one()
        if self.reminder_calendar_event_id:
            return self.reminder_calendar_event_id
        if 'calendar_event_id' in self._fields and self.calendar_event_id:
            return self.calendar_event_id
        return self.env['calendar.event']

    def _tcrm_sync_reminders(self):
        """Create or update calendar + To-Do reminders for CRM lead activities."""
        if self.env.context.get('tcrm_reminder_sync_running'):
            return
        activities = self.with_context(
            tcrm_reminder_sync_running=True,
            tcrm_skip_reminder_sync=True,
        )
        for activity in activities:
            if activity.res_model != 'crm.lead' or not activity.res_id:
                continue
            lead = self.env['crm.lead'].browse(activity.res_id).exists()
            if not lead:
                continue
            need_calendar = bool(activity.date_deadline) or activity.activity_category == 'meeting'
            if need_calendar:
                activity._tcrm_sync_calendar_reminder(lead)
            activity._tcrm_sync_todo_reminder(lead)

    def _tcrm_crm_deep_link(self, lead):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        return '%s/web#id=%s&model=crm.lead&view_type=form' % (base, lead.id)

    def _tcrm_reminder_title(self, lead):
        self.ensure_one()
        activity_label = self.activity_type_id.name or self.summary or _('Aktivite')
        return '%s — %s' % (lead.display_name, activity_label)

    def _tcrm_todo_description(self, lead):
        self.ensure_one()
        activity_label = self.activity_type_id.name or self.summary or _('Aktivite')
        responsible = self.user_id.display_name if self.user_id else ''
        customer = lead.partner_id.display_name if lead.partner_id else (lead.contact_name or '')
        project_name = ''
        if 'propertio_project_id' in lead._fields and lead.propertio_project_id:
            project_name = lead.propertio_project_id.display_name
        notes = ''
        if self.note and not is_html_empty(self.note):
            notes = html2plaintext(self.note).strip()
        deep_link = self._tcrm_crm_deep_link(lead)
        lines = [
            _('Lead / Fırsat: %s') % lead.display_name,
            _('Aktivite Tipi: %s') % activity_label,
            _('Son Tarih: %s') % (self.date_deadline or '-'),
            _('Sorumlu: %s') % (responsible or '-'),
            _('Müşteri / Kişi: %s') % (customer or '-'),
            _('Proje: %s') % (project_name or '-'),
            _('Notlar: %s') % (notes or '-'),
            _('CRM Bağlantısı: %s') % deep_link,
        ]
        return Markup('<br/>').join(escape(line) for line in lines)

    def _tcrm_sync_calendar_reminder(self, lead):
        self.ensure_one()
        if not self.date_deadline and self.activity_category != 'meeting':
            return
        deadline = self.date_deadline or fields.Date.context_today(self)
        user = self.user_id or self.env.user
        partner = user.partner_id
        event_name = self._tcrm_reminder_title(lead)
        start_dt = datetime.combine(deadline, time(9, 0, 0))
        stop_dt = datetime.combine(deadline, time(10, 0, 0))
        vals = {
            'name': event_name,
            'start': start_dt,
            'stop': stop_dt,
            'allday': False,
            'user_id': user.id,
            'description': self._tcrm_todo_description(lead),
        }
        if partner:
            vals['partner_ids'] = [(4, partner.id)]
        if 'opportunity_id' in self.env['calendar.event']._fields:
            vals['opportunity_id'] = lead.id
        event = self._tcrm_reminder_calendar_event()
        # Avoid activity↔calendar write loops (deadline / meeting sync).
        Event = self.env['calendar.event'].with_context(
            tcrm_skip_reminder_sync=True,
            tcrm_reminder_sync_running=True,
            calendar_event_meeting_update=True,
            mail_create_nolog=True,
            mail_notrack=True,
        )
        if event:
            Event.browse(event.ids).write(vals)
        else:
            event = Event.create(vals)
            write_vals = {'reminder_calendar_event_id': event.id}
            if 'calendar_event_id' in self._fields and not self.calendar_event_id:
                write_vals['calendar_event_id'] = event.id
            self.with_context(
                tcrm_skip_reminder_sync=True,
                tcrm_reminder_sync_running=True,
                calendar_event_meeting_update=True,
            ).write(write_vals)
        # Ensure responsible remains linked (partner_ids and/or attendees).
        attendee_partners = event.attendee_ids.mapped('partner_id') | event.partner_ids
        if partner and partner not in attendee_partners:
            event.with_context(
                tcrm_skip_reminder_sync=True,
                calendar_event_meeting_update=True,
            ).write({'partner_ids': [(4, partner.id)]})

    def _tcrm_sync_todo_reminder(self, lead):
        self.ensure_one()
        user = self.user_id or self.env.user
        deadline = self.date_deadline or fields.Date.context_today(self)
        # project.task.date_deadline is Datetime
        deadline_dt = fields.Datetime.to_datetime(deadline)
        vals = {
            'name': self._tcrm_reminder_title(lead),
            'description': self._tcrm_todo_description(lead),
            'date_deadline': deadline_dt,
            'user_ids': [(6, 0, user.ids)],
        }
        if self.todo_task_id:
            self.todo_task_id.write(vals)
        else:
            task = self.env['project.task'].create(vals)
            self.with_context(tcrm_skip_reminder_sync=True).write({'todo_task_id': task.id})

    def _tcrm_close_reminders(self, done=True):
        """Mark linked To-Dos done / cancel calendar events when activity ends."""
        for activity in self:
            task = activity.todo_task_id
            if task and task.state not in ('1_done', '1_canceled'):
                task.state = '1_done' if done else '1_canceled'
            event = activity._tcrm_reminder_calendar_event()
            if event:
                # Prefer soft cancel when available
                if 'active' in event._fields:
                    event.write({'active': False})
                else:
                    event.unlink()

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('tcrm_skip_reminder_sync'):
            return res
        # When archived (done/cancel path) close reminders
        if 'active' in vals and not vals.get('active'):
            self._tcrm_close_reminders(done=True)
            return res
        sync_keys = {
            'date_deadline', 'summary', 'note', 'user_id',
            'activity_type_id', 'calendar_event_id',
        }
        if sync_keys.intersection(vals):
            crm_acts = self.filtered(
                lambda a: a.res_model == 'crm.lead' and (
                    a.todo_task_id or a.reminder_calendar_event_id
                    or ('calendar_event_id' in a._fields and a.calendar_event_id)
                )
            )
            if crm_acts:
                crm_acts._tcrm_sync_reminders()
        return res

    def unlink(self):
        crm_acts = self.filtered(lambda a: a.res_model == 'crm.lead')
        if crm_acts:
            crm_acts._tcrm_close_reminders(done=False)
        return super().unlink()

    def _action_done(self, feedback=False, attachment_ids=None):
        crm_acts = self.filtered(lambda a: a.res_model == 'crm.lead')
        if crm_acts:
            crm_acts._tcrm_close_reminders(done=True)
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)
