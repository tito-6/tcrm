# -*- coding: utf-8 -*-
import re
import uuid

try:
    from tcrm import models, fields, api
    from tcrm.exceptions import ValidationError, UserError
except ImportError:
    from odoo import models, fields, api
    from odoo.exceptions import ValidationError, UserError

IMMUTABLE_LEAD_IDEMPOTENCY_FIELDS = {
    'tcrm_idempotency_scope',
    'tcrm_idempotency_key',
    'tcrm_idempotency_payload_sha256',
    'tcrm_external_submission_id',
}


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    tcrm_idempotency_scope = fields.Char(
        string='TCRM Idempotency Scope', readonly=True, index=True,
    )
    tcrm_idempotency_key = fields.Char(
        string='TCRM Idempotency Key', readonly=True, index=True,
    )
    tcrm_idempotency_payload_sha256 = fields.Char(
        string='TCRM Idempotency Payload SHA-256', readonly=True,
    )
    tcrm_external_submission_id = fields.Char(
        string='TCRM External Submission ID', readonly=True,
    )

    def init(self):
        super().init()
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS unique_tcrm_lead_idempotency_scope_key
            ON crm_lead (tcrm_idempotency_scope, tcrm_idempotency_key)
            WHERE tcrm_idempotency_scope IS NOT NULL AND tcrm_idempotency_key IS NOT NULL;
        """)

    _sql_constraints = [
        (
            'unique_tcrm_lead_idempotency_scope_key',
            'unique(tcrm_idempotency_scope, tcrm_idempotency_key)',
            'Combination of TCRM idempotency scope and key must be unique per lead.',
        ),
    ]

    def write(self, vals):
        modified = IMMUTABLE_LEAD_IDEMPOTENCY_FIELDS.intersection(vals.keys())
        if modified:
            raise UserError(
                'TCRM integration identity fields are immutable after creation: %s'
                % ', '.join(sorted(modified))
            )
        return super().write(vals)

    @api.constrains(
        'tcrm_idempotency_scope',
        'tcrm_idempotency_key',
        'tcrm_idempotency_payload_sha256',
    )
    def _check_idempotency_fields_integrity(self):
        for record in self:
            present = [
                bool(record.tcrm_idempotency_scope),
                bool(record.tcrm_idempotency_key),
                bool(record.tcrm_idempotency_payload_sha256),
            ]
            if any(present) and not all(present):
                raise ValidationError(
                    'TCRM lead idempotency fields must be all present or all absent.'
                )
            if record.tcrm_idempotency_key:
                try:
                    parsed = uuid.UUID(str(record.tcrm_idempotency_key))
                    if parsed.version != 4:
                        raise ValueError('not v4')
                except (ValueError, TypeError, AttributeError):
                    raise ValidationError(
                        'TCRM lead idempotency key must be a valid UUID v4.'
                    )
            if record.tcrm_idempotency_payload_sha256:
                if not re.match(r'^[a-f0-9]{64}$', str(record.tcrm_idempotency_payload_sha256)):
                    raise ValidationError(
                        'TCRM lead idempotency payload hash must be 64 lowercase hex characters.'
                    )
