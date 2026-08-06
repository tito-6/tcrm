# -*- coding: utf-8 -*-
try:
    from tcrm import http, fields
    from tcrm.http import request
except ImportError:
    from odoo import http, fields
    from odoo.http import request

import json
import logging
import hashlib
import hmac
import os
import time
import psycopg2
from psycopg2 import IntegrityError, errorcodes

_logger = logging.getLogger(__name__)

IDEMPOTENCY_SCOPE = 'akod_lead_webhook:v1'


class LeadWebhook(http.Controller):
    """Webhook endpoints for external lead sources"""

    @http.route('/webhook/akod/lead', type='http', auth='public', methods=['POST'], csrf=False)
    def create_lead_akod(self, **kwargs):
        """
        V1 Signed Lead Webhook with Read-Only Tenant Public UUID Verification,
        Re-raised Unexpected Integrity Errors, and Ingestion-Context Lead Idempotency.
        """
        correlation_id = request.httprequest.headers.get('X-TCRM-Correlation-ID', '')
        try:
            headers = request.httprequest.headers
            sig_version = headers.get('X-TCRM-Signature-Version') or 'v1'
            timestamp_str = headers.get('X-TCRM-Timestamp', '')
            provided_tenant_uuid = headers.get('X-TCRM-Tenant', '')
            idempotency_key = headers.get('X-TCRM-Idempotency-Key', '')
            provided_sig = headers.get('X-TCRM-Signature', '')

            # 1. Require Tenant Header & Validate Against Dedicated Database Tenant Public UUID
            if not provided_tenant_uuid:
                _logger.warning("Tenant header missing correlation=%s", correlation_id)
                return request.make_json_response({'success': False, 'error': 'TENANT_HEADER_MISSING'}, status=400)

            # Load authoritative tenant public UUID (Read-only helper)
            ir_model = request.env['tcrm.integration.request'].sudo()
            db_tenant_uuid = ir_model._get_tenant_public_uuid()

            if not db_tenant_uuid:
                _logger.error("Tenant public UUID not configured correlation=%s", correlation_id)
                return request.make_json_response({'success': False, 'error': 'TENANT_IDENTITY_NOT_CONFIGURED'}, status=503)

            # Constant-time comparison of tenant public UUID (Rejects 'master', dbname, or wrong UUID)
            if not hmac.compare_digest(provided_tenant_uuid, db_tenant_uuid):
                _logger.warning("Tenant identity mismatch correlation=%s", correlation_id)
                return request.make_json_response({'success': False, 'error': 'TENANT_IDENTITY_MISMATCH'}, status=403)

            # 2. Raw Body Hash & V1 Canonical Payload
            raw_body_bytes = request.httprequest.data
            raw_body_hash = hashlib.sha256(raw_body_bytes).hexdigest()

            canonical_payload = f"{sig_version}\nPOST\n/webhook/akod/lead\n{timestamp_str}\n{provided_tenant_uuid}\n{idempotency_key}\n{raw_body_hash}"

            # 3. HMAC Signature Calculation & Constant-Time Comparison
            secret = os.environ.get('TCRM_LEAD_SECRET', 'tcrm_lead_secret_key_2026').encode('utf-8')
            expected_sig = hmac.new(secret, canonical_payload.encode('utf-8'), hashlib.sha256).hexdigest()

            if not provided_sig or not hmac.compare_digest(provided_sig, expected_sig):
                _logger.warning("AKOD lead webhook signature mismatch correlation=%s", correlation_id)
                return request.make_json_response({'success': False, 'error': 'Invalid signature'}, status=401)

            # 4. Replay Window Check (< 300s)
            try:
                ts = float(timestamp_str)
                if abs(time.time() - ts) > 300:
                    return request.make_json_response({'success': False, 'error': 'Timestamp expired'}, status=401)
            except Exception:
                return request.make_json_response({'success': False, 'error': 'Invalid timestamp'}, status=401)

            # 5. Validate JSON Payload AFTER Signature Verification
            try:
                data = json.loads(raw_body_bytes.decode('utf-8'))
            except Exception:
                return request.make_json_response({'success': False, 'error': 'Malformed JSON body'}, status=400)

            # 6. RETENTION FALLBACK CHECK: Search CRM Lead by Scope + Key
            lead_env = request.env['crm.lead'].sudo()
            existing_lead = lead_env.search([
                ('tcrm_idempotency_scope', '=', IDEMPOTENCY_SCOPE),
                ('tcrm_idempotency_key', '=', idempotency_key)
            ], limit=1)

            if existing_lead:
                if existing_lead.tcrm_idempotency_payload_sha256 != raw_body_hash:
                    return request.make_json_response({'success': False, 'error': 'Idempotency key payload mismatch'}, status=409)

                return request.make_json_response({
                    'success': True,
                    'lead_id': existing_lead.id,
                    'correlationId': correlation_id,
                    'replayed': True,
                    'message': 'Duplicate request handled idempotently via lead record'
                }, status=200)

            ir_record = None
            is_retry = False

            # 7. ATOMIC CREATE-FIRST INTEGRATION REQUEST (Re-raise Unexpected Exceptions)
            try:
                with request.env.cr.savepoint():
                    ir_record = ir_model.create({
                        'tenant_identifier': provided_tenant_uuid,
                        'integration': 'akod_lead_webhook',
                        'scope': IDEMPOTENCY_SCOPE,
                        'route': '/webhook/akod/lead',
                        'idempotency_key': idempotency_key,
                        'request_body_sha256': raw_body_hash,
                        'correlation_id': correlation_id,
                        'state': 'pending',
                        'target_model': 'crm.lead'
                    })
            except IntegrityError as exc:
                pgcode = getattr(exc, 'pgcode', None)
                constraint_name = getattr(getattr(exc, 'diag', None), 'constraint_name', None)

                if pgcode != errorcodes.UNIQUE_VIOLATION or constraint_name != 'unique_tenant_integration_idempotency':
                    _logger.error("Unexpected IntegrityError correlation=%s pgcode=%s constraint=%s", correlation_id, pgcode, constraint_name)
                    raise

                existing_ir = ir_model.search([
                    ('tenant_identifier', '=', provided_tenant_uuid),
                    ('integration', '=', 'akod_lead_webhook'),
                    ('idempotency_key', '=', idempotency_key)
                ], limit=1)

                if existing_ir:
                    if existing_ir.request_body_sha256 != raw_body_hash:
                        return request.make_json_response({'success': False, 'error': 'Idempotency key payload mismatch'}, status=409)

                    if existing_ir.state == 'completed':
                        return request.make_json_response({
                            'success': True,
                            'lead_id': existing_ir.target_record_id,
                            'correlationId': correlation_id,
                            'replayed': True,
                            'message': 'Duplicate request handled idempotently'
                        }, status=200)
                    elif existing_ir.state == 'pending':
                        return request.make_json_response({
                            'success': True,
                            'correlationId': correlation_id,
                            'replayed': True,
                            'message': 'Request currently processing'
                        }, status=202)
                    elif existing_ir.state == 'failed':
                        if existing_ir.retry_count >= 3:
                            return request.make_json_response({'success': False, 'error': 'Max retries exceeded for failed request'}, status=500)
                        ir_record = existing_ir
                        is_retry = True

            # 8. CREATE CRM LEAD (With tcrm_integration_ingestion=True Context)
            lead = None
            lead_data = {
                'name': data.get('name', 'Web Lead'),
                'contact_name': data.get('contact_name') or data.get('name'),
                'email_from': data.get('email_from') or data.get('email'),
                'phone': data.get('phone'),
                'partner_name': data.get('partner_name') or data.get('company'),
                'description': f"{data.get('description', '')}\nCorrelation-ID: {correlation_id}",
                'tcrm_idempotency_scope': IDEMPOTENCY_SCOPE,
                'tcrm_idempotency_key': idempotency_key,
                'tcrm_idempotency_payload_sha256': raw_body_hash,
                'type': 'lead',
            }

            # Meta CAPI match params (fbc/fbp/ip/ua/event_id) — real values only
            event_id = None
            try:
                from tcrm.addons.meta_leads.services.meta_capi_helpers import capture_browser_context
                ctx = capture_browser_context(data=data, httprequest=request.httprequest)
                for key in (
                    'meta_fbc', 'meta_fbp', 'meta_client_ip', 'meta_client_user_agent',
                    'meta_event_source_url', 'meta_event_id', 'city', 'zip',
                ):
                    if key in lead_env._fields and ctx.get(key):
                        lead_data[key] = ctx[key]
                event_id = ctx.get('meta_event_id') or None
                if not event_id:
                    event_id = f'evt_akod_{idempotency_key[:16] if idempotency_key else int(time.time())}'
                    if 'meta_event_id' in lead_env._fields:
                        lead_data['meta_event_id'] = event_id
                country_code = ctx.get('_country_code')
                if country_code and 'country_id' in lead_env._fields:
                    country = request.env['res.country'].sudo().search(
                        [('code', '=ilike', country_code)], limit=1,
                    )
                    if country:
                        lead_data['country_id'] = country.id
                if ctx.get('_gender') and 'meta_gender' in lead_env._fields:
                    g = str(ctx['_gender'])[:1]
                    if g in ('m', 'f'):
                        lead_data['meta_gender'] = g
                if ctx.get('_dob') and 'meta_date_of_birth' in lead_env._fields:
                    raw = str(ctx['_dob']).strip()
                    digits = ''.join(c for c in raw if c.isdigit())
                    if len(digits) == 8:
                        lead_data['meta_date_of_birth'] = f'{digits[0:4]}-{digits[4:6]}-{digits[6:8]}'
                    elif len(raw) == 10 and raw[4] == '-' and raw[7] == '-':
                        lead_data['meta_date_of_birth'] = raw
            except Exception as capi_ctx_exc:
                _logger.warning('Meta tracking capture skipped correlation=%s: %s', correlation_id, capi_ctx_exc)

            try:
                with request.env.cr.savepoint():
                    lead = lead_env.with_context(tcrm_integration_ingestion=True).create(lead_data)
            except IntegrityError as exc:
                pgcode = getattr(exc, 'pgcode', None)
                constraint_name = getattr(getattr(exc, 'diag', None), 'constraint_name', None)

                if pgcode != errorcodes.UNIQUE_VIOLATION or constraint_name != 'unique_tcrm_lead_idempotency_scope_key':
                    _logger.error("Unexpected Lead IntegrityError correlation=%s pgcode=%s constraint=%s", correlation_id, pgcode, constraint_name)
                    raise

                lead = lead_env.search([
                    ('tcrm_idempotency_scope', '=', IDEMPOTENCY_SCOPE),
                    ('tcrm_idempotency_key', '=', idempotency_key)
                ], limit=1)

                if lead and lead.tcrm_idempotency_payload_sha256 != raw_body_hash:
                    return request.make_json_response({'success': False, 'error': 'Idempotency key payload mismatch'}, status=409)

            # Fire Meta CAPI Lead (deduped with Pixel via shared event_id)
            if lead and not getattr(lead, 'meta_capi_lead_event_sent', False):
                try:
                    from tcrm.addons.meta_leads.services.meta_capi_helpers import fire_capi_for_lead
                    fire_capi_for_lead(
                        request.env, lead,
                        event_name='Lead',
                        event_id=event_id or getattr(lead, 'meta_event_id', None),
                    )
                except Exception as capi_exc:
                    _logger.warning('Meta CAPI Lead fire failed correlation=%s: %s', correlation_id, capi_exc)

            # 9. Mark Completed & Link Target Record
            write_vals = {
                'state': 'completed',
                'target_record_id': lead.id if lead else 0,
                'response_code': 200,
                'completed_at': fields.Datetime.now()
            }
            if is_retry:
                write_vals['retry_count'] = ir_record.retry_count + 1
                write_vals['last_retry_at'] = fields.Datetime.now()

            if ir_record:
                ir_record.write(write_vals)

            _logger.info("Created AKOD lead correlation=%s lead_id=%s", correlation_id, lead.id if lead else 0)

            return request.make_json_response({
                'success': True,
                'lead_id': lead.id if lead else 0,
                'event_id': event_id or (lead.meta_event_id if lead and hasattr(lead, 'meta_event_id') else None),
                'correlationId': correlation_id,
                'message': 'Lead processed successfully'
            })

        except Exception as exc:
            _logger.exception("Sanitized outer error boundary caught exception correlation=%s: %s", correlation_id, exc)
            return request.make_json_response({'success': False, 'error': 'INTERNAL_PROCESSING_ERROR', 'correlationId': correlation_id}, status=500)
