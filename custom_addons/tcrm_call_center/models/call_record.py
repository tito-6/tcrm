# -*- coding: utf-8 -*-
"""Tenant-local call records."""
from __future__ import annotations

import logging

from tcrm import api, fields, models, _
from tcrm.exceptions import AccessError, UserError

from ..services.phone import mask_phone, normalize_e164, assert_allowed_destination
from ..services.dial_token import issue_dial_token
from ..services.providers import get_provider

_logger = logging.getLogger(__name__)

OUTCOME_SELECTION = [
    ('reached', 'Ulaşıldı'),
    ('not_reached', 'Ulaşılamadı'),
    ('busy', 'Meşgul'),
    ('no_answer', 'Cevapsız'),
    ('wrong_number', 'Yanlış Numara'),
    ('callback', 'Tekrar Aranacak'),
    ('appointment', 'Randevu Oluşturuldu'),
    ('interested', 'İlgileniyor'),
    ('not_interested', 'İlgilenmiyor'),
    ('opportunity', 'Satış Fırsatı Oluşturuldu'),
]


class TcrmCallRecord(models.Model):
    _name = 'tcrm.call.record'
    _description = 'Santral Call Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'display_name'

    name = fields.Char(string='Referans', required=True, copy=False, default='New', readonly=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one('res.users', string='Temsilci', required=True, default=lambda self: self.env.user, index=True)
    team_id = fields.Many2one('crm.team', string='Satış Ekibi', index=True)
    lead_id = fields.Many2one('crm.lead', string='Fırsat / Aday', index=True, ondelete='set null')
    partner_id = fields.Many2one('res.partner', string='Müşteri', index=True, ondelete='set null')
    project_id = fields.Many2one('propertio.project', string='Proje', index=True, ondelete='set null')
    contact_name = fields.Char(
        string='Aranan Kişi', compute='_compute_contact_name', store=True,
        help='Aranan aday/fırsat veya müşteri adı.')

    destination_number = fields.Char(string='Hedef Numara', required=True)
    destination_masked = fields.Char(string='Hedef (Gizli)', readonly=True)
    caller_id = fields.Char(string='Arayan Kimliği', readonly=True)
    direction = fields.Selection(
        [('outbound', 'Giden'), ('inbound', 'Gelen')],
        string='Yön', default='outbound', required=True)
    provider = fields.Selection([('twilio', 'Twilio')], string='Sağlayıcı', default='twilio', required=True)

    provider_call_sid = fields.Char(string='Provider Call SID', index=True, copy=False)
    parent_call_sid = fields.Char(string='Parent Call SID', index=True, copy=False)
    child_call_sid = fields.Char(string='Child Call SID', index=True, copy=False)
    dial_token_fingerprint = fields.Char(string='Dial Token Fingerprint', copy=False, index=True)
    dial_token_used = fields.Boolean(default=False, copy=False)

    status = fields.Selection([
        ('pending', 'Bekliyor'),
        ('queued', 'Sırada'),
        ('initiated', 'Başlatıldı'),
        ('ringing', 'Çalıyor'),
        ('in-progress', 'Görüşülüyor'),
        ('completed', 'Tamamlandı'),
        ('busy', 'Meşgul'),
        ('failed', 'Başarısız'),
        ('no-answer', 'Cevapsız'),
        ('canceled', 'İptal Edildi'),
    ], string='Durum', default='pending', required=True, index=True, tracking=True)

    start_time = fields.Datetime()
    ringing_time = fields.Datetime()
    answer_time = fields.Datetime()
    end_time = fields.Datetime()
    duration = fields.Integer(string='Süre (sn)', default=0)
    billable_duration = fields.Integer(string='Ücretli Süre (sn)', default=0)

    recording_state = fields.Selection([
        ('none', 'Yok'),
        ('pending', 'Hazırlanıyor'),
        ('ready', 'Hazır'),
        ('failed', 'Başarısız'),
        ('deleted', 'Silindi'),
    ], string='Kayıt Durumu', default='none', required=True)
    recording_sid = fields.Char(index=True, copy=False)
    recording_duration = fields.Integer(default=0)
    recording_channels = fields.Integer(default=0)
    recording_ids = fields.One2many('tcrm.call.recording', 'call_id', string='Recordings')

    outcome = fields.Selection(OUTCOME_SELECTION, string='Sonuç')
    notes = fields.Text(string='Notlar')
    followup_activity_id = fields.Many2one('mail.activity', string='Takip Aktivitesi', copy=False)
    provider_error_code = fields.Char()
    provider_error_message = fields.Char()
    user_error_message = fields.Char(string='User-facing Error')

    # Diagnostics
    sdk_version = fields.Char(string='SDK Version', readonly=True)
    browser_os = fields.Char(string='Browser / OS', readonly=True)
    selected_edge = fields.Char(string='Selected Edge', readonly=True)
    codec = fields.Char(string='Codec', readonly=True)
    rtt = fields.Integer(string='RTT (ms)', readonly=True)
    jitter = fields.Integer(string='Jitter (ms)', readonly=True)
    packet_loss = fields.Float(string='Packet Loss (%)', readonly=True)
    mos = fields.Float(string='MOS', readonly=True)
    warning_events = fields.Text(string='Warning Events', readonly=True)
    microphone_device = fields.Char(string='Microphone Device', readonly=True)
    connection_type = fields.Char(string='Connection Type', readonly=True)

    active_browser_session = fields.Boolean(default=False, help='One active browser call per user.')

    _sql_constraints = [
        ('provider_call_sid_uniq', 'unique(provider_call_sid)', 'Provider Call SID must be unique.'),
    ]

    @api.depends('name', 'destination_masked', 'status')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s — %s (%s)' % (rec.name, rec.destination_masked or '***', rec.status)

    @api.depends('lead_id', 'lead_id.contact_name', 'lead_id.partner_name', 'lead_id.name',
                 'partner_id', 'partner_id.display_name')
    def _compute_contact_name(self):
        """Aranan kişinin adı: önce aday/fırsat kişisi, sonra müşteri."""
        for rec in self:
            name = False
            if rec.lead_id:
                name = rec.lead_id.contact_name or rec.lead_id.partner_name or rec.lead_id.name
            if not name and rec.partner_id:
                name = rec.partner_id.display_name
            rec.contact_name = name or ''

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('tcrm.call.record') or 'CALL'
            dest = vals.get('destination_number')
            if dest:
                e164 = normalize_e164(dest)
                assert_allowed_destination(e164)
                vals['destination_number'] = e164
                vals['destination_masked'] = mask_phone(e164)
        return super().create(vals_list)

    def write(self, vals):
        if 'destination_number' in vals:
            # Destination is immutable after authorization / dial start.
            for rec in self:
                if rec.status != 'pending' or rec.dial_token_used:
                    raise UserError(_('Arama yetkilendirmesinden sonra hedef numara değiştirilemez.'))
            e164 = normalize_e164(vals['destination_number'])
            assert_allowed_destination(e164)
            vals['destination_number'] = e164
            vals['destination_masked'] = mask_phone(e164)
        return super().write(vals)

    def _crm_target(self):
        self.ensure_one()
        if self.lead_id:
            self.lead_id.check_access('read')
            return self.lead_id
        if self.partner_id:
            self.partner_id.check_access('read')
            return self.partner_id
        raise AccessError(_('CRM kaydı erişilebilir değil.'))

    @api.model
    def action_prepare_outbound(self, *, res_model, res_id, phone=None):
        """Create pending call + dial token for an accessible CRM record."""
        if not self.env.user.has_group('tcrm_call_center.group_santral_user'):
            raise AccessError(_('Santral Kullanıcısı yetkisi gerekli.'))

        config = self.env['tcrm.call.provider.config'].get_for_company(require_enabled=True)
        if not config:
            raise UserError(_('Santral yapılandırılmamış'))

        active_calls = self.search([
            ('user_id', '=', self.env.uid),
            ('active_browser_session', '=', True),
            ('status', 'in', ['pending', 'queued', 'initiated', 'ringing', 'in-progress']),
        ])
        for active in active_calls:
            # If it's just pending (never actually started dialing), we can safely cancel it.
            # If it's older than 15 minutes, we can also assume it's stale and cancel it.
            if active.status == 'pending' or (fields.Datetime.now() - active.create_date).total_seconds() > 900:
                active.action_hangup_local()
            else:
                raise UserError(_('Zaten devam eden bir aramanız var.'))

        lead = self.env['crm.lead'].browse()
        partner = self.env['res.partner'].browse()
        project = self.env['propertio.project'].browse()
        team = self.env['crm.team'].browse()

        if res_model == 'crm.lead':
            lead = self.env['crm.lead'].browse(int(res_id))
            lead.check_access('read')
            if not lead.exists():
                raise AccessError(_('Lead bulunamadı.'))
            partner = lead.partner_id
            project = getattr(lead, 'propertio_project_id', self.env['propertio.project'])
            team = lead.team_id
            phone = phone or lead.phone or lead.mobile or (partner.phone if partner else False) or (partner.mobile if partner else False)
        elif res_model == 'res.partner':
            partner = self.env['res.partner'].browse(int(res_id))
            partner.check_access('read')
            if not partner.exists():
                raise AccessError(_('Kişi bulunamadı.'))
            phone = phone or partner.phone or partner.mobile
        else:
            raise UserError(_('Desteklenmeyen kayıt türü.'))

        if not phone:
            raise UserError(_('Aranacak telefon numarası yok.'))

        e164 = normalize_e164(phone)
        assert_allowed_destination(e164)

        call = self.create({
            'company_id': config.company_id.id,
            'user_id': self.env.uid,
            'team_id': team.id if team else False,
            'lead_id': lead.id if lead else False,
            'partner_id': partner.id if partner else False,
            'project_id': project.id if project else False,
            'destination_number': e164,
            'caller_id': config.verified_caller_id,
            'direction': 'outbound',
            'provider': config.provider,
            'status': 'pending',
            'recording_state': 'pending' if config.recording_enabled else 'none',
            'active_browser_session': True,
            'start_time': fields.Datetime.now(),
        })
        dial_token = issue_dial_token(
            self.env, call_id=call.id, destination=e164, user_id=self.env.uid, ttl_seconds=120,
        )
        import hashlib
        call.sudo().write({
            'dial_token_fingerprint': hashlib.sha256(dial_token.encode()).hexdigest(),
        })
        return call, dial_token, config

    def action_open_dialer(self):
        self.ensure_one()
        self.check_access('read')
        return {
            'type': 'ir.actions.client',
            'tag': 'tcrm_call_center.dialer',
            'name': _('Santral'),
            'target': 'new',
            'context': {
                'call_id': self.id,
                'lead_id': self.lead_id.id if self.lead_id else False,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'record_name': (self.lead_id or self.partner_id).display_name if (self.lead_id or self.partner_id) else self.display_name,
                'phone_masked': self.destination_masked,
                'project_name': self.project_id.display_name if self.project_id else '',
            },
        }

    def action_save_wrapup(self, outcome=None, notes=None, create_followup=False, followup_summary=None, followup_date=None):
        self.ensure_one()
        self.check_access('write')
        vals = {}
        if outcome:
            vals['outcome'] = outcome
        if notes is not None:
            vals['notes'] = notes
        if vals:
            self.write(vals)

        target = self.lead_id or self.partner_id
        if target and notes:
            # Avoid duplicate chatter spam: only post once per wrap-up write.
            body = _('Çağrı notu (%s): %s') % (self.name, notes)
            target.message_post(body=body, message_type='comment', subtype_xmlid='mail.mt_note')

        if create_followup and target and not self.followup_activity_id:
            activity_type = self.env.ref('mail.mail_activity_data_call', raise_if_not_found=False) \
                or self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            if activity_type:
                summary = followup_summary or _('Santral takip: %s') % (self.destination_masked or self.name)
                deadline = followup_date or fields.Date.context_today(self)
                activity = target.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary=summary,
                    note=notes or '',
                    date_deadline=deadline,
                    user_id=self.env.uid,
                )
                self.followup_activity_id = activity.id
                # Reuse Propertio reminder sync when available on crm.lead activities.
                if self.lead_id and hasattr(activity, '_tcrm_sync_reminders'):
                    activity._tcrm_sync_reminders()
        return True

    def _apply_status_event(self, *, call_status, call_sid=None, parent_sid=None, duration=None,
                            error_code=None, error_message=None, timestamp=None):
        self.ensure_one()
        vals = {}
        is_child_leg = bool(parent_sid)
        
        if is_child_leg:
            vals['child_call_sid'] = call_sid
            if not self.parent_call_sid:
                vals['parent_call_sid'] = parent_sid
            if not self.provider_call_sid:
                vals['provider_call_sid'] = parent_sid
        else:
            if call_sid and not self.provider_call_sid:
                vals['provider_call_sid'] = call_sid

        status = (call_status or '').lower()
        mapping = {
            'queued': 'queued',
            'initiated': 'initiated',
            'ringing': 'ringing',
            'in-progress': 'in-progress',
            'answered': 'in-progress',
            'completed': 'completed',
            'busy': 'busy',
            'failed': 'failed',
            'no-answer': 'no-answer',
            'canceled': 'canceled',
            'cancelled': 'canceled',
        }
        
        mapped_status = mapping.get(status)
        
        # Avoid masking child errors with parent gateway hangups
        if not is_child_leg and mapped_status in ('busy', 'failed', 'completed', 'canceled'):
            if self.status in ('failed', 'busy'):
                mapped_status = self.status
            elif mapped_status == 'busy':
                # Parent client leg should not trigger 'busy' status directly
                mapped_status = 'completed'

        if mapped_status:
            vals['status'] = mapped_status

        now = timestamp or fields.Datetime.now()
        if mapped_status == 'ringing' and not self.ringing_time:
            vals['ringing_time'] = now
        if mapped_status in ('in-progress', 'answered') and not self.answer_time:
            vals['answer_time'] = now
        if mapped_status in ('completed', 'busy', 'failed', 'no-answer', 'canceled', 'cancelled'):
            vals['end_time'] = now
            vals['active_browser_session'] = False

        if duration is not None:
            try:
                vals['duration'] = int(duration)
            except (TypeError, ValueError):
                pass

        # Only track errors from the child PSTN leg, or if no child leg error exists
        if is_child_leg or (not self.provider_error_code and str(error_code) != '31005'):
            if error_code:
                vals['provider_error_code'] = str(error_code)[:64]
            if error_message:
                vals['provider_error_message'] = str(error_message)[:500]
                config = self.env['tcrm.call.provider.config'].get_for_company(self.company_id)
                if config:
                    try:
                        provider = get_provider(self.env, config)
                        user_msg = provider.map_trial_error(error_code, error_message)
                        if user_msg:
                            vals['user_error_message'] = user_msg
                    except Exception:
                        pass

        if vals:
            self.sudo().write(vals)

    def action_hangup_local(self):
        self.ensure_one()
        self.write({
            'status': 'canceled' if self.status in ('pending', 'queued', 'initiated', 'ringing') else self.status,
            'end_time': fields.Datetime.now(),
            'active_browser_session': False,
        })
        config = self.env['tcrm.call.provider.config'].get_for_company(self.company_id)
        if config:
            try:
                provider = get_provider(self.env, config)
                for sid in (self.child_call_sid, self.parent_call_sid, self.provider_call_sid):
                    if sid:
                        provider.terminate_call_leg(sid)
            except Exception as exc:
                _logger.warning('Santral: action_hangup_local provider error for call %s: %s', self.id, exc)

