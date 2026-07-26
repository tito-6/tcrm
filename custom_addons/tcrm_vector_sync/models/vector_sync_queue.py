# Part of TCRM Vector Sync. See LICENSE for details.

"""Queue model: pending payloads sent to remote /ingest by cron."""

import logging

import requests

from tcrm import api, fields, models

_logger = logging.getLogger(__name__)

BATCH_SIZE = 50
TIMEOUT = 30


class VectorSyncQueue(models.Model):
    _name = 'tcrm.vector.sync.queue'
    _description = 'TCRM Vector Sync Queue'
    _order = 'id asc'

    model = fields.Char(string='Model', required=True, index=True)
    record_id = fields.Integer(string='Record ID', required=True, index=True)
    text = fields.Text(string='Text')
    action = fields.Selection([
        ('upsert', 'Upsert'),
        ('delete', 'Delete'),
    ], string='Action', required=True, default='upsert')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ], string='State', required=True, default='pending', index=True)
    error_message = fields.Text(string='Error Message')

    def _build_payload(self):
        return {
            'model': self.model,
            'record_id': self.record_id,
            'text': self.text or '',
            'action': self.action,
        }

    @api.model
    def _cron_process_queue(self):
        """Process a batch of pending queue rows: POST to {tcrm.ai_base_url}/ingest."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('tcrm.ai_base_url', '').strip()
        if not base_url:
            return
        base_url = base_url.rstrip('/')
        ingest_url = f'{base_url}/ingest'

        pending = self.sudo().search([('state', '=', 'pending')], limit=BATCH_SIZE, order='id asc')
        for row in pending:
            try:
                payload = row._build_payload()
                resp = requests.post(ingest_url, json=payload, timeout=TIMEOUT)
                if resp.status_code in (200, 201, 204):
                    row.state = 'sent'
                    row.error_message = False
                else:
                    row.state = 'failed'
                    row.error_message = f'HTTP {resp.status_code}: {resp.text[:500] if resp.text else ""}'
                    _logger.warning("Vector ingest failed for %s %s: %s", row.model, row.record_id, row.error_message)
            except requests.RequestException as e:
                row.state = 'failed'
                row.error_message = str(e)[:500]
                _logger.warning("Vector ingest request failed for %s %s: %s", row.model, row.record_id, e)
            except Exception as e:
                row.state = 'failed'
                row.error_message = str(e)[:500]
                _logger.exception("Vector sync queue process error for %s %s", row.model, row.record_id)
        if pending:
            self.env.cr.commit()
