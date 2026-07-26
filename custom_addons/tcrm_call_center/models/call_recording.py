# -*- coding: utf-8 -*-
"""Call recording metadata + protected attachment storage."""
from __future__ import annotations

import base64
import logging

from tcrm import api, fields, models, _
from tcrm.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class TcrmCallRecording(models.Model):
    _name = 'tcrm.call.recording'
    _description = 'Santral Call Recording'
    _order = 'id desc'

    name = fields.Char(required=True, default='Recording')
    company_id = fields.Many2one('res.company', required=True, index=True, default=lambda self: self.env.company)
    call_id = fields.Many2one('tcrm.call.record', required=True, ondelete='cascade', index=True)
    lead_id = fields.Many2one(related='call_id.lead_id', store=True, index=True)
    partner_id = fields.Many2one(related='call_id.partner_id', store=True, index=True)
    provider = fields.Selection([('twilio', 'Twilio')], default='twilio', required=True)
    recording_sid = fields.Char(required=True, index=True, copy=False)
    status = fields.Selection([
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('absent', 'Absent'),
        ('deleted', 'Deleted'),
    ], default='processing', required=True)
    duration = fields.Integer(default=0)
    channels = fields.Integer(default=0)
    media_content_type = fields.Char(default='audio/mpeg')
    attachment_id = fields.Many2one('ir.attachment', string='Stored Attachment', ondelete='set null', copy=False)
    retention_deadline = fields.Date()
    playback_count = fields.Integer(default=0)
    last_played_at = fields.Datetime()
    last_played_by = fields.Many2one('res.users')
    playback_url = fields.Char(compute='_compute_playback_url')

    def _compute_playback_url(self):
        for rec in self:
            rec.playback_url = '/tcrm/call/recording/%s' % rec.id if rec.id else False

    _sql_constraints = [
        ('recording_sid_uniq', 'unique(recording_sid)', 'Recording SID must be unique.'),
    ]

    def _check_playback_access(self):
        self.ensure_one()
        if not self.env.user.has_group('tcrm_call_center.group_santral_recording_listen'):
            raise AccessError(_('Çağrı kaydı dinleme yetkisi gerekli.'))
        self.call_id.check_access('read')
        if self.call_id.lead_id:
            self.call_id.lead_id.check_access('read')
        if self.call_id.partner_id:
            self.call_id.partner_id.check_access('read')
        if self.status != 'completed':
            raise UserError(_('Kayıt henüz hazır değil.'))

    def _check_download_access(self):
        self._check_playback_access()
        config = self.env['tcrm.call.provider.config'].get_for_company(self.company_id)
        if not self.env.user.has_group('tcrm_call_center.group_santral_recording_download'):
            raise AccessError(_('Çağrı kaydı indirme yetkisi gerekli.'))
        if config and not config.allow_recording_download:
            raise AccessError(_('Bu kiracı için kayıt indirme kapalı.'))

    def audit_playback(self):
        self.ensure_one()
        self.sudo().write({
            'playback_count': self.playback_count + 1,
            'last_played_at': fields.Datetime.now(),
            'last_played_by': self.env.uid,
        })
        _logger.info(
            'Santral recording playback recording_id=%s call_id=%s user_id=%s db=%s',
            self.id, self.call_id.id, self.env.uid, self.env.cr.dbname,
        )

    def _fetch_provider_media(self) -> tuple[bytes, str]:
        """Server-side fetch using tenant credentials (no browser URL exposure)."""
        self.ensure_one()
        if self.attachment_id and self.attachment_id.datas:
            return base64.b64decode(self.attachment_id.datas), self.media_content_type or 'audio/mpeg'
        config = self.env['tcrm.call.provider.config'].sudo().get_for_company(self.company_id)
        if not config:
            raise UserError(_('Santral yapılandırılmamış'))
        from ..services.providers import get_provider
        provider = get_provider(self.env, config)
        content, ctype = provider.fetch_recording_bytes(self.recording_sid)
        if content and (config.recording_storage == 'attachment' or self.env.context.get('force_store_attachment')):
            att = self.env['ir.attachment'].sudo().create({
                'name': 'santral-%s.mp3' % self.recording_sid,
                'type': 'binary',
                'datas': base64.b64encode(content),
                'mimetype': ctype,
                'res_model': self._name,
                'res_id': self.id,
                'company_id': self.company_id.id,
            })
            self.sudo().write({'attachment_id': att.id, 'media_content_type': ctype})
        return content, ctype

    def get_media_bytes(self) -> tuple[bytes, str]:
        self.ensure_one()
        self._check_playback_access()
        return self._fetch_provider_media()

    def server_store_from_provider(self):
        """Webhook/cron path — no end-user ACL."""
        self.ensure_one()
        return self.with_context(force_store_attachment=True)._fetch_provider_media()

    @api.model
    def cron_purge_expired(self):
        today = fields.Date.context_today(self)
        expired = self.sudo().search([
            ('retention_deadline', '!=', False),
            ('retention_deadline', '<', today),
            ('status', '!=', 'deleted'),
        ])
        for rec in expired:
            if rec.attachment_id:
                rec.attachment_id.unlink()
            rec.write({'status': 'deleted', 'attachment_id': False})
            rec.call_id.write({'recording_state': 'deleted'})
        return True
