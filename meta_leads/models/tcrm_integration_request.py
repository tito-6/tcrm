from odoo import models, fields, api

class TcrmIntegrationRequest(models.Model):
    _name = 'tcrm.integration.request'
    _description = 'TCRM Integration Request'

    tenant_identifier = fields.Char(string='Tenant Identifier', required=True, index=True)
    integration = fields.Char(string='Integration', required=True, index=True, default='akod_lead_webhook')
    idempotency_key = fields.Char(string='Idempotency Key', required=True, index=True)
    
    payload_sha256 = fields.Char(string='Payload SHA-256')
    correlation_id = fields.Char(string='Correlation ID')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('error', 'Error'),
    ], string='State', default='pending', required=True)
    
    target_lead_id = fields.Many2one('crm.lead', string='Target Lead')
    response_code = fields.Integer(string='Response Code')
    error_code = fields.Char(string='Error Code')

    _sql_constraints = [
        ('unique_tenant_integration_idempotency', 'unique(tenant_identifier, integration, idempotency_key)', 'The idempotency key must be unique per tenant and integration.')
    ]

