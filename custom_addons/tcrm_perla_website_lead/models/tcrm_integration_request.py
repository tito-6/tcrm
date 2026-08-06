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
IMMUTABLE_FIELDS = {
    'tenant_identifier',
    'integration',
    'route',
    'idempotency_key',
    'request_body_sha256',
    'scope',
}


class TcrmIntegrationRequest(models.Model):
    _name = 'tcrm.integration.request'
    _description = 'TCRM Integration Request & Idempotency Store'

    tenant_identifier = fields.Char(string='Tenant Identifier', required=True, index=True)
    integration = fields.Char(string='Integration Name', required=True, index=True)
    scope = fields.Char(string='Idempotency Scope', required=True, index=True)
    route = fields.Char(string='Request Route', required=True)
    idempotency_key = fields.Char(string='Idempotency Key', required=True, index=True)
    request_body_sha256 = fields.Char(string='Body SHA-256 Hash', required=True)
    correlation_id = fields.Char(string='Correlation ID', index=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
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
            CREATE UNIQUE INDEX IF NOT EXISTS unique_tenant_integration_idempotency
            ON tcrm_integration_request (tenant_identifier, integration, idempotency_key);
        """)

    @api.model
    def _get_tenant_public_uuid(self):
        """Read-only: authoritative tenant public UUID (never generated here)."""
        val = self.env['ir.config_parameter'].sudo().get_param('tcrm.tenant_public_uuid')
        if not val:
            return None
        try:
            parsed = uuid.UUID(str(val))
            if parsed.version != 4:
                return None
            return str(parsed)
        except (ValueError, TypeError, AttributeError):
            return None

    @api.constrains('target_model')
    def _check_target_model_allowlist(self):
        for record in self:
            if record.target_model not in ALLOWED_TARGET_MODELS:
                raise ValidationError('Target model is not allowed.')

    def write(self, vals):
        modified_immutable = IMMUTABLE_FIELDS.intersection(vals.keys())
        if modified_immutable:
            raise UserError(
                'Cannot modify immutable idempotency identity fields: %s'
                % ', '.join(sorted(modified_immutable))
            )
        if vals.get('state') == 'completed' and 'completed_at' not in vals:
            vals = dict(vals, completed_at=fields.Datetime.now())
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get('allow_retention_cleanup'):
            raise UserError(
                'Manual deletion of integration request idempotency records is prohibited.'
            )
        return super().unlink()
