import uuid
import re
try:
    from tcrm import models, fields, api
    from tcrm.exceptions import ValidationError, UserError
except ImportError:
    from odoo import models, fields, api
    from odoo.exceptions import ValidationError, UserError

import requests
import os
import logging
from ..services.meta_creative_service import MetaCreativeService

_logger = logging.getLogger(__name__)

IMMUTABLE_LEAD_IDEMPOTENCY_FIELDS = {
    'tcrm_idempotency_scope',
    'tcrm_idempotency_key',
    'tcrm_idempotency_payload_sha256',
    'tcrm_external_submission_id'
}


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # TCRM Lead-Level Immutable Idempotency Fields (NO DEFAULT SCOPE)
    tcrm_idempotency_scope = fields.Char(string='TCRM Idempotency Scope', readonly=True, index=True)
    tcrm_idempotency_key = fields.Char(string='TCRM Idempotency Key', index=True, readonly=True)
    tcrm_idempotency_payload_sha256 = fields.Char(string='TCRM Idempotency Payload SHA-256', readonly=True)
    tcrm_external_submission_id = fields.Char(string='TCRM External Submission ID', readonly=True)

    def init(self):
        super().init()
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS unique_tcrm_lead_idempotency_scope_key 
            ON crm_lead (tcrm_idempotency_scope, tcrm_idempotency_key) 
            WHERE tcrm_idempotency_scope IS NOT NULL AND tcrm_idempotency_key IS NOT NULL;
        """)

    # Meta lead data fields
    meta_form_id = fields.Char(string='Meta Form ID', readonly=True)
    meta_ad_id = fields.Char(string='Meta Ad ID', readonly=True)
    meta_ad_name = fields.Char(string='Meta Ad Name', readonly=True)
    meta_leadgen_id = fields.Char(string='Meta Leadgen ID', readonly=True)
    meta_page_id = fields.Char(string='Meta Page ID', readonly=True)
    meta_campaign_id = fields.Char(string='Meta Campaign ID', readonly=True)
    meta_campaign_name = fields.Char(string='Campaign', readonly=True)
    meta_adset_id = fields.Char(string='Meta Adset ID', readonly=True)
    meta_adset_name = fields.Char(string='Ad Set', readonly=True)
    meta_platform = fields.Selection([
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('messenger', 'Messenger')
    ], string='Platform', readonly=True)
    
    # Submission timestamp
    submitted_on = fields.Datetime(string='Submitted On', readonly=True, help='Date and time when the lead was submitted on Facebook')
    meta_creative_id = fields.Char(string='Meta Creative ID', readonly=True)
    meta_creative_fetch_method = fields.Char(string='Creative Fetch Method', readonly=True)
    meta_creative_fetch_error = fields.Text(string='Creative Fetch Error', readonly=True)
    meta_creative_type = fields.Char(string='Creative Type', readonly=True)
    meta_creative_resolution_quality = fields.Char(string='Resolution Quality', readonly=True)
    meta_creative_title = fields.Char(string='Creative Title', readonly=True)
    meta_creative_body = fields.Text(string='Creative Body', readonly=True)
    meta_creative_cta = fields.Char(string='Creative CTA', readonly=True)
    meta_creative_media_url = fields.Char(string='Media URL', readonly=True)
    meta_creative_high_res_url = fields.Char(string='High Res URL', readonly=True)
    meta_creative_effective_story_id = fields.Char(string='Effective Story ID', readonly=True)
    meta_creative_asset_feed_spec = fields.Text(string='Asset Feed Spec', readonly=True)
    meta_creative_image_html = fields.Html(string='Creative Image', readonly=True)
    meta_creative_video_embed = fields.Html(string='Creative Video', readonly=True)
    meta_creative_video_embed_html = fields.Html(string='Creative Video Embed HTML', readonly=True)
    
    # Computed field for form answers display
    form_answers_display = fields.Html(
        string='Form Answers',
        compute='_compute_form_answers_display',
        store=False,
    )

    _sql_constraints = [
        ('unique_tcrm_lead_idempotency_scope_key',
         'unique(tcrm_idempotency_scope, tcrm_idempotency_key)',
         'Combination of TCRM idempotency scope and key must be unique per lead.')
    ]

    @api.depends('description', 'meta_form_answers', 'meta_raw_payload')
    def _compute_form_answers_display(self):
        """Render Meta lead form answers as readable HTML for the CRM form."""
        import html
        import json

        for lead in self:
            pairs = lead._extract_form_answer_pairs()
            if not pairs:
                lead.form_answers_display = False
                continue
            rows = []
            for key, value in pairs:
                rows.append(
                    "<tr>"
                    f"<th style=\"text-align:left;padding:6px 10px;border-bottom:1px solid #eee;"
                    f"white-space:nowrap;vertical-align:top;\">{html.escape(str(key))}</th>"
                    f"<td style=\"padding:6px 10px;border-bottom:1px solid #eee;\">"
                    f"{html.escape(str(value))}</td>"
                    "</tr>"
                )
            lead.form_answers_display = (
                "<table style=\"width:100%;border-collapse:collapse;font-size:13px;\">"
                f"{''.join(rows)}</table>"
            )

    def _extract_form_answer_pairs(self):
        """Collect (label, value) pairs from Meta form payload / description."""
        self.ensure_one()
        pairs = []

        raw_answers = getattr(self, 'meta_form_answers', None) or False
        if raw_answers:
            pairs = self._pairs_from_form_answers_blob(raw_answers)
            if pairs:
                return pairs

        raw_payload = getattr(self, 'meta_raw_payload', None) or False
        if raw_payload:
            pairs = self._pairs_from_meta_payload(raw_payload)
            if pairs:
                return pairs

        desc = self.description or ''
        if 'Form Answers:' in desc:
            section = desc.split('Form Answers:', 1)[1]
            for line in section.splitlines():
                line = line.strip().lstrip('•').strip()
                if not line or ':' not in line:
                    continue
                key, value = line.split(':', 1)
                key, value = key.strip(), value.strip()
                if key and value:
                    pairs.append((key, value))
        return pairs

    @staticmethod
    def _pairs_from_form_answers_blob(blob):
        import json
        text = (blob or '').strip()
        if not text:
            return []
        # JSON object / list
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return [(str(k), v if not isinstance(v, (list, dict)) else json.dumps(v, ensure_ascii=False))
                        for k, v in data.items() if v not in (None, '', [])]
            if isinstance(data, list):
                out = []
                for item in data:
                    if isinstance(item, dict):
                        name = item.get('name') or item.get('question') or item.get('key')
                        values = item.get('values') or item.get('value') or item.get('answer')
                        if isinstance(values, list):
                            values = ', '.join(str(v) for v in values)
                        if name and values not in (None, ''):
                            out.append((str(name), str(values)))
                return out
        except Exception:
            pass
        # Plain "key: value" lines
        out = []
        for line in text.splitlines():
            line = line.strip().lstrip('•').strip()
            if ':' in line:
                key, value = line.split(':', 1)
                if key.strip() and value.strip():
                    out.append((key.strip(), value.strip()))
        return out

    @staticmethod
    def _pairs_from_meta_payload(blob):
        import json
        try:
            data = json.loads(blob)
        except Exception:
            return []
        field_data = data.get('field_data') or data.get('field_data_list') or []
        if isinstance(data.get('entry'), list):
            # webhook envelope — dig for field_data
            for entry in data['entry']:
                for change in entry.get('changes', []) or []:
                    value = (change.get('value') or {})
                    if value.get('field_data'):
                        field_data = value['field_data']
                        break
        out = []
        if isinstance(field_data, list):
            for item in field_data:
                if not isinstance(item, dict):
                    continue
                name = item.get('name') or item.get('question')
                values = item.get('values') or item.get('value')
                if isinstance(values, list):
                    values = ', '.join(str(v) for v in values)
                if name and values not in (None, ''):
                    out.append((str(name), str(values)))
        elif isinstance(field_data, dict):
            out = [(str(k), str(v)) for k, v in field_data.items() if v not in (None, '')]
        return out

    def write(self, vals):
        # Unconditional server-side ORM immutability on idempotency identity fields after creation
        modified_immutable = IMMUTABLE_LEAD_IDEMPOTENCY_FIELDS.intersection(vals.keys())
        if modified_immutable:
            raise UserError(f"TCRM integration identity fields are immutable after creation: {', '.join(modified_immutable)}")
        return super(CrmLead, self).write(vals)

    @api.constrains('tcrm_idempotency_scope', 'tcrm_idempotency_key', 'tcrm_idempotency_payload_sha256')
    def _check_idempotency_fields_integrity(self):
        """Enforce that idempotency fields are either all present or all absent and strictly formatted."""
        for record in self:
            fields_present = [
                bool(record.tcrm_idempotency_scope),
                bool(record.tcrm_idempotency_key),
                bool(record.tcrm_idempotency_payload_sha256)
            ]
            if any(fields_present) and not all(fields_present):
                raise ValidationError("TCRM Lead idempotency fields (scope, key, payload_sha256) must be either all present or all absent.")

            if record.tcrm_idempotency_key:
                try:
                    uuid.UUID(str(record.tcrm_idempotency_key))
                except (ValueError, TypeError, AttributeError):
                    raise ValidationError("TCRM Lead idempotency key must be a valid UUID format.")

            if record.tcrm_idempotency_payload_sha256:
                if not re.match(r'^[a-f0-9]{64}$', str(record.tcrm_idempotency_payload_sha256)):
                    raise ValidationError("TCRM Lead idempotency payload hash must be exactly 64 lowercase hexadecimal characters.")