# -*- coding: utf-8 -*-
import logging
import uuid
from datetime import datetime, timedelta

try:
    from tcrm import models, fields, api
    from tcrm.exceptions import ValidationError, UserError
except ImportError:
    from odoo import models, fields, api
    from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

ALLOWED_TARGET_MODELS = ['crm.lead']
IMMUTABLE_FIELDS = {'tenant_identifier', 'integration', 'route', 'idempotency_key', 'request_body_sha256', 'scope'}


class TcrmIntegrationRequest(models.Model):
    _name = 'tcrm.integration.request'
    _description = 'TCRM Integration Request & Idempotency Store'

    tenant_identifier = fields.Char(string='Tenant Identifier', required=True, index=True)
    integration = fields.Char(string='Integration Name', required=True, default='akod_lead_webhook', index=True)
    scope = fields.Char(string='Idempotency Scope', required=True, index=True)
    route = fields.Char(string='Request Route', required=True, default='/webhook/akod/lead')
    idempotency_key = fields.Char(string='Idempotency Key', required=True, index=True)
    request_body_sha256 = fields.Char(string='Body SHA-256 Hash', required=True)
    correlation_id = fields.Char(string='Correlation ID', index=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], string='Status', default='pending', required=True, index=True)

    target_model = fields.Char(string='Target Model', default='crm.lead', required=True)
    target_record_id = fields.Integer(string='Target Record ID')
    response_code = fields.Integer(string='Response Code', default=200)
    safe_error_code = fields.Char(string='Safe Error Code')
    failure_stage = fields.Char(string='Failure Stage')

    retry_count = fields.Integer(string='Retry Count', default=0)
    last_retry_at = fields.Datetime(string='Last Retry At')
    next_retry_at = fields.Datetime(string='Next Retry At')
    completed_at = fields.Datetime(string='Completed At')

    def init(self):
        super().init()
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'tcrm_integration_request'
            );
        """)
        if self.env.cr.fetchone()[0]:
            self.env.cr.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS unique_tenant_integration_idempotency 
                ON tcrm_integration_request (tenant_identifier, integration, idempotency_key);
            """)

    @api.model
    def _get_tenant_public_uuid(self):
        """Strictly read-only helper: Retrieve authoritative tenant public UUID."""
        val = self.env['ir.config_parameter'].sudo().get_param('tcrm.tenant_public_uuid')
        if not val:
            return None
        try:
            parsed = uuid.UUID(str(val))
            return str(parsed)
        except (ValueError, TypeError, AttributeError):
            return None

    @api.constrains('target_model')
    def _check_target_model_allowlist(self):
        for record in self:
            if record.target_model not in ALLOWED_TARGET_MODELS:
                raise ValidationError(f"Target model '{record.target_model}' is not in the allowed security list.")

    def write(self, vals):
        # Make idempotency identity immutable after creation
        modified_immutable = IMMUTABLE_FIELDS.intersection(vals.keys())
        if modified_immutable:
            raise UserError(f"Cannot modify immutable idempotency identity fields: {', '.join(modified_immutable)}")
        if 'state' in vals and vals['state'] == 'completed' and 'completed_at' not in vals:
            vals['completed_at'] = fields.Datetime.now()
        return super(TcrmIntegrationRequest, self).write(vals)

    def unlink(self):
        # Prevent manual deletion except when explicitly triggered by system retention job context
        if not self.env.context.get('allow_retention_cleanup'):
            raise UserError("Manual deletion of integration request idempotency records is strictly prohibited.")
        return super(TcrmIntegrationRequest, self).unlink()

    @api.model
    def _cron_reconcile_stale_requests(self):
        """Cron job: transition pending requests older than 15 minutes to failed"""
        stale_threshold = datetime.now() - timedelta(minutes=15)
        stale_records = self.search([
            ('state', '=', 'pending'),
            ('create_date', '<', stale_threshold)
        ])
        if stale_records:
            _logger.info(f"Reconciling {len(stale_records)} stale pending integration requests")
            stale_records.write({
                'state': 'failed',
                'response_code': 504,
                'safe_error_code': 'TIMEOUT_STALE_PENDING',
                'failure_stage': 'pending_reconciliation'
            })

    @api.model
    def _cron_cleanup_old_integration_requests(self, retention_days=90):
        """Batch retention cleanup job for completed integration requests older than retention threshold"""
        cleanup_threshold = datetime.now() - timedelta(days=retention_days)
        old_records = self.search([
            ('state', '=', 'completed'),
            ('create_date', '<', cleanup_threshold)
        ], limit=500)
        if old_records:
            _logger.info(f"Cleaning up {len(old_records)} old completed integration request records")
            old_records.with_context(allow_retention_cleanup=True).unlink()
