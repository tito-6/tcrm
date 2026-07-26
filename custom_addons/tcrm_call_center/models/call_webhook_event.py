# -*- coding: utf-8 -*-
"""Idempotent webhook event store."""
from __future__ import annotations

import hashlib
import json

from tcrm import api, fields, models


class TcrmCallWebhookEvent(models.Model):
    _name = 'tcrm.call.webhook.event'
    _description = 'Santral Webhook Event'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', required=True, index=True)
    call_id = fields.Many2one('tcrm.call.record', ondelete='set null', index=True)
    provider = fields.Selection([('twilio', 'Twilio')], default='twilio', required=True)
    event_type = fields.Selection([
        ('call_status', 'Call Status'),
        ('recording_status', 'Recording Status'),
    ], required=True, index=True)
    provider_sid = fields.Char(index=True)
    fingerprint = fields.Char(required=True, index=True)
    payload_safe = fields.Text(help='Redacted/safe subset of webhook fields')
    processed = fields.Boolean(default=False)
    processed_at = fields.Datetime()

    _sql_constraints = [
        ('fingerprint_uniq', 'unique(fingerprint)', 'Webhook event already processed.'),
    ]

    @api.model
    def make_fingerprint(self, *, event_type, provider_sid, status, timestamp, extra=''):
        raw = '|'.join([
            self.env.cr.dbname,
            event_type or '',
            provider_sid or '',
            status or '',
            timestamp or '',
            extra or '',
        ])
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    @api.model
    def register_or_skip(self, *, company, call, event_type, provider_sid, status, timestamp, safe_payload):
        fp = self.make_fingerprint(
            event_type=event_type,
            provider_sid=provider_sid,
            status=status,
            timestamp=timestamp,
            extra=json.dumps(safe_payload, sort_keys=True, default=str)[:500],
        )
        existing = self.sudo().search([('fingerprint', '=', fp)], limit=1)
        if existing:
            return existing, True
        try:
            event = self.sudo().create({
                'company_id': company.id,
                'call_id': call.id if call else False,
                'event_type': event_type,
                'provider_sid': provider_sid,
                'fingerprint': fp,
                'payload_safe': json.dumps(safe_payload, ensure_ascii=False)[:4000],
                'processed': False,
            })
            return event, False
        except Exception:
            # Unique constraint race → treat as duplicate.
            self.env.cr.rollback()
            existing = self.sudo().search([('fingerprint', '=', fp)], limit=1)
            return existing, True
