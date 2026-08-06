# -*- coding: utf-8 -*-
"""Signed Perla Villaları website lead webhook — POST /webhook/tcrm/lead."""
import hashlib
import hmac
import json
import logging
import re
import time
import uuid
from urllib.parse import urlparse

try:
    from tcrm import http, fields
    from tcrm.http import request
except ImportError:
    from odoo import http, fields
    from odoo.http import request

from psycopg2 import IntegrityError, errorcodes

_logger = logging.getLogger(__name__)

IDEMPOTENCY_SCOPE = 'perla_website_lead:v1'
INTEGRATION_NAME = 'perla_website_lead'
ROUTE_PATH = '/webhook/tcrm/lead'
MAX_BODY_BYTES = 65536
REPLAY_WINDOW_SECONDS = 300
APPROVED_PAGE_HOSTS = frozenset({
    'perlavillalari.com',
    'www.perlavillalari.com',
})
ALLOWED_LANGUAGES = frozenset({'tr', 'en', 'de', 'ru', 'ar'})
ALLOWED_PAYLOAD_KEYS = frozenset({
    'name', 'email', 'phone', 'message', 'source', 'page_url', 'language',
})
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
CONTROL_CHAR_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


class PerlaWebsiteLeadWebhook(http.Controller):
    """Public signed lead intake for Perla Villaları website only."""

    @http.route(
        ROUTE_PATH,
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def create_lead_perla(self, **kwargs):
        started = time.monotonic()
        correlation_id = ''
        try:
            headers = request.httprequest.headers
            correlation_id = (headers.get('X-TCRM-Correlation-ID') or '').strip()

            # 1. Enable gate (tenant-local; missing/false → reject, no side effects)
            if not self._is_enabled():
                return self._json(
                    {'success': False, 'error': 'NOT_FOUND'},
                    status=404,
                    correlation_id=correlation_id,
                )

            # 2. Method (route already restricts; defend in depth)
            if request.httprequest.method != 'POST':
                return self._json(
                    {'success': False, 'error': 'METHOD_NOT_ALLOWED'},
                    status=405,
                    correlation_id=correlation_id,
                )

            # 3. Content-Type
            content_type = (request.httprequest.content_type or '').split(';')[0].strip().lower()
            if content_type != 'application/json':
                return self._json(
                    {'success': False, 'error': 'UNSUPPORTED_MEDIA_TYPE'},
                    status=415,
                    correlation_id=correlation_id,
                )

            # 4. Exact raw body (reject oversized before parse)
            raw_body_bytes = request.httprequest.data or b''
            if len(raw_body_bytes) > MAX_BODY_BYTES:
                return self._json(
                    {'success': False, 'error': 'PAYLOAD_TOO_LARGE'},
                    status=413,
                    correlation_id=correlation_id,
                )

            # 5. Required headers
            sig_version = (headers.get('X-TCRM-Signature-Version') or '').strip()
            timestamp_str = (headers.get('X-TCRM-Timestamp') or '').strip()
            provided_tenant_uuid = (headers.get('X-TCRM-Tenant') or '').strip()
            idempotency_key = (headers.get('X-TCRM-Idempotency-Key') or '').strip()
            provided_sig = (headers.get('X-TCRM-Signature') or '').strip()

            missing = []
            if not sig_version:
                missing.append('X-TCRM-Signature-Version')
            if not timestamp_str:
                missing.append('X-TCRM-Timestamp')
            if not provided_tenant_uuid:
                missing.append('X-TCRM-Tenant')
            if not idempotency_key:
                missing.append('X-TCRM-Idempotency-Key')
            if not correlation_id:
                missing.append('X-TCRM-Correlation-ID')
            if not provided_sig:
                missing.append('X-TCRM-Signature')
            if missing:
                return self._json(
                    {'success': False, 'error': 'MISSING_HEADERS'},
                    status=400,
                    correlation_id=correlation_id,
                )

            # Correlation / idempotency UUID format
            if not self._is_uuid(correlation_id):
                return self._json(
                    {'success': False, 'error': 'INVALID_CORRELATION_ID'},
                    status=400,
                    correlation_id=correlation_id,
                )
            if not self._is_uuid_v4(idempotency_key):
                return self._json(
                    {'success': False, 'error': 'INVALID_IDEMPOTENCY_KEY'},
                    status=400,
                    correlation_id=correlation_id,
                )

            # 6. Signature version
            if sig_version != 'v1':
                return self._json(
                    {'success': False, 'error': 'UNSUPPORTED_SIGNATURE_VERSION'},
                    status=401,
                    correlation_id=correlation_id,
                )

            # 7. Timestamp / replay window
            try:
                ts = float(timestamp_str)
                if abs(time.time() - ts) > REPLAY_WINDOW_SECONDS:
                    return self._json(
                        {'success': False, 'error': 'TIMESTAMP_EXPIRED'},
                        status=401,
                        correlation_id=correlation_id,
                    )
            except (TypeError, ValueError):
                return self._json(
                    {'success': False, 'error': 'INVALID_TIMESTAMP'},
                    status=401,
                    correlation_id=correlation_id,
                )

            # 8–9. Tenant public UUID (read-only; never generated here)
            ir_model = request.env['tcrm.integration.request'].sudo()
            db_tenant_uuid = ir_model._get_tenant_public_uuid()
            if not db_tenant_uuid:
                _logger.error(
                    'perla_website_lead tenant uuid missing correlation=%s',
                    correlation_id,
                )
                return self._json(
                    {'success': False, 'error': 'TENANT_IDENTITY_NOT_CONFIGURED'},
                    status=503,
                    correlation_id=correlation_id,
                )
            if not self._is_uuid_v4(provided_tenant_uuid):
                return self._json(
                    {'success': False, 'error': 'INVALID_TENANT'},
                    status=403,
                    correlation_id=correlation_id,
                )
            if not hmac.compare_digest(provided_tenant_uuid, db_tenant_uuid):
                _logger.warning(
                    'perla_website_lead tenant mismatch correlation=%s',
                    correlation_id,
                )
                return self._json(
                    {'success': False, 'error': 'TENANT_IDENTITY_MISMATCH'},
                    status=403,
                    correlation_id=correlation_id,
                )

            # 10–12. Raw-body hash + HMAC (before JSON parse)
            secret = self._get_webhook_secret()
            if not secret:
                _logger.error(
                    'perla_website_lead secret missing correlation=%s',
                    correlation_id,
                )
                return self._json(
                    {'success': False, 'error': 'INTEGRATION_NOT_CONFIGURED'},
                    status=503,
                    correlation_id=correlation_id,
                )

            if not re.match(r'^[a-f0-9]{64}$', provided_sig):
                return self._json(
                    {'success': False, 'error': 'INVALID_SIGNATURE'},
                    status=401,
                    correlation_id=correlation_id,
                )

            raw_body_hash = hashlib.sha256(raw_body_bytes).hexdigest()
            canonical = (
                f'{sig_version}\nPOST\n{ROUTE_PATH}\n{timestamp_str}\n'
                f'{provided_tenant_uuid}\n{idempotency_key}\n{raw_body_hash}'
            )
            expected_sig = hmac.new(
                secret.encode('utf-8'),
                canonical.encode('utf-8'),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(provided_sig, expected_sig):
                _logger.warning(
                    'perla_website_lead signature mismatch correlation=%s',
                    correlation_id,
                )
                return self._json(
                    {'success': False, 'error': 'INVALID_SIGNATURE'},
                    status=401,
                    correlation_id=correlation_id,
                )

            # 13. Durable idempotency (create-first)
            ir_record, early = self._claim_or_replay(
                ir_model=ir_model,
                tenant_uuid=provided_tenant_uuid,
                idempotency_key=idempotency_key,
                raw_body_hash=raw_body_hash,
                correlation_id=correlation_id,
            )
            if early is not None:
                self._log_result(correlation_id, early.status_code, early, started)
                return early

            # 14–15. Parse + validate business payload
            try:
                data = json.loads(raw_body_bytes.decode('utf-8'))
            except Exception:
                self._fail_ir(ir_record, 400, 'MALFORMED_JSON')
                return self._json(
                    {'success': False, 'error': 'MALFORMED_JSON'},
                    status=400,
                    correlation_id=correlation_id,
                )

            ok, err, status = self._validate_payload(data)
            if not ok:
                self._fail_ir(ir_record, status, err)
                return self._json(
                    {'success': False, 'error': err},
                    status=status,
                    correlation_id=correlation_id,
                )

            # 16. Trusted assignment configuration
            assignment, assign_err = self._resolve_assignment()
            if assign_err:
                self._fail_ir(ir_record, 503, assign_err)
                return self._json(
                    {'success': False, 'error': assign_err},
                    status=503,
                    correlation_id=correlation_id,
                )

            # 17. Create CRM lead (or race-safe replay)
            lead, lead_err, lead_status = self._create_lead(
                data=data,
                assignment=assignment,
                idempotency_key=idempotency_key,
                raw_body_hash=raw_body_hash,
                correlation_id=correlation_id,
            )
            if lead_err:
                self._fail_ir(ir_record, lead_status, lead_err)
                return self._json(
                    {'success': False, 'error': lead_err},
                    status=lead_status,
                    correlation_id=correlation_id,
                )

            # 18. Mark integration request completed
            ir_record.write({
                'state': 'completed',
                'target_record_id': lead.id,
                'response_code': 200,
                'completed_at': fields.Datetime.now(),
            })

            resp = self._json(
                {
                    'success': True,
                    'lead_id': lead.id,
                    'replayed': False,
                    'correlation_id': correlation_id,
                },
                status=200,
                correlation_id=correlation_id,
            )
            _logger.info(
                'perla_website_lead ok correlation=%s lead_id=%s duration_ms=%s',
                correlation_id,
                lead.id,
                int((time.monotonic() - started) * 1000),
            )
            return resp

        except Exception:
            _logger.exception(
                'perla_website_lead internal error correlation=%s',
                correlation_id,
            )
            return self._json(
                {
                    'success': False,
                    'error': 'INTERNAL_PROCESSING_ERROR',
                    'correlation_id': correlation_id or None,
                },
                status=500,
                correlation_id=correlation_id,
            )

    # ------------------------------------------------------------------ helpers

    def _json(self, payload, status=200, correlation_id=''):
        if correlation_id and 'correlation_id' not in payload:
            payload = dict(payload, correlation_id=correlation_id)
        return request.make_json_response(payload, status=status)

    def _log_result(self, correlation_id, status_code, response, started):
        _logger.info(
            'perla_website_lead status=%s correlation=%s duration_ms=%s',
            status_code,
            correlation_id,
            int((time.monotonic() - started) * 1000),
        )

    def _param(self, key, default=None):
        return request.env['ir.config_parameter'].sudo().get_param(key, default)

    def _is_enabled(self):
        val = (self._param('tcrm.public_lead.enabled') or '').strip().lower()
        return val in ('1', 'true', 'yes', 'on')

    def _get_webhook_secret(self):
        secret = (self._param('tcrm.public_lead.webhook_secret') or '').strip()
        if len(secret) < 32:
            return None
        return secret

    @staticmethod
    def _is_uuid(value):
        try:
            uuid.UUID(str(value))
            return True
        except (ValueError, TypeError, AttributeError):
            return False

    @staticmethod
    def _is_uuid_v4(value):
        try:
            parsed = uuid.UUID(str(value))
            return parsed.version == 4
        except (ValueError, TypeError, AttributeError):
            return False

    def _claim_or_replay(self, ir_model, tenant_uuid, idempotency_key, raw_body_hash, correlation_id):
        """Atomic create-first idempotency claim. Returns (record, early_response|None)."""
        try:
            with request.env.cr.savepoint():
                ir_record = ir_model.create({
                    'tenant_identifier': tenant_uuid,
                    'integration': INTEGRATION_NAME,
                    'scope': IDEMPOTENCY_SCOPE,
                    'route': ROUTE_PATH,
                    'idempotency_key': idempotency_key,
                    'request_body_sha256': raw_body_hash,
                    'correlation_id': correlation_id,
                    'state': 'pending',
                    'target_model': 'crm.lead',
                })
            return ir_record, None
        except IntegrityError as exc:
            pgcode = getattr(exc, 'pgcode', None)
            constraint_name = getattr(getattr(exc, 'diag', None), 'constraint_name', None)
            if pgcode != errorcodes.UNIQUE_VIOLATION or constraint_name != 'unique_tenant_integration_idempotency':
                raise

            existing = ir_model.search([
                ('tenant_identifier', '=', tenant_uuid),
                ('integration', '=', INTEGRATION_NAME),
                ('idempotency_key', '=', idempotency_key),
            ], limit=1)
            if not existing:
                raise

            if existing.request_body_sha256 != raw_body_hash:
                return None, self._json(
                    {
                        'success': False,
                        'error': 'IDEMPOTENCY_PAYLOAD_MISMATCH',
                        'correlation_id': correlation_id,
                    },
                    status=409,
                    correlation_id=correlation_id,
                )

            if existing.state == 'completed':
                return existing, self._json(
                    {
                        'success': True,
                        'lead_id': existing.target_record_id,
                        'replayed': True,
                        'correlation_id': correlation_id,
                    },
                    status=200,
                    correlation_id=correlation_id,
                )

            if existing.state == 'pending':
                return existing, self._json(
                    {
                        'success': False,
                        'error': 'CONCURRENT_REQUEST',
                        'correlation_id': correlation_id,
                    },
                    status=409,
                    correlation_id=correlation_id,
                )

            # failed → allow retry by reclaiming the same row
            existing.write({
                'state': 'pending',
                'safe_error_code': False,
                'failure_stage': False,
                'retry_count': existing.retry_count + 1,
                'last_retry_at': fields.Datetime.now(),
            })
            return existing, None

    def _fail_ir(self, ir_record, code, error):
        if not ir_record:
            return
        try:
            ir_record.write({
                'state': 'failed',
                'response_code': code,
                'safe_error_code': error,
                'failure_stage': 'processing',
            })
        except Exception:
            _logger.exception('perla_website_lead failed to mark IR failed')

    def _validate_payload(self, data):
        if not isinstance(data, dict):
            return False, 'INVALID_PAYLOAD', 422
        if any(isinstance(v, (dict, list)) for v in data.values()):
            return False, 'INVALID_PAYLOAD', 422
        unexpected = set(data.keys()) - ALLOWED_PAYLOAD_KEYS
        if unexpected:
            return False, 'UNEXPECTED_FIELDS', 422

        name = (data.get('name') or '').strip() if data.get('name') is not None else ''
        email = (data.get('email') or '').strip() if data.get('email') is not None else ''
        phone = (data.get('phone') or '').strip() if data.get('phone') is not None else ''
        message = data.get('message') if data.get('message') is not None else ''
        source = (data.get('source') or '').strip() if data.get('source') is not None else ''
        page_url = (data.get('page_url') or '').strip() if data.get('page_url') is not None else ''
        language = (data.get('language') or '').strip().lower() if data.get('language') is not None else ''

        for raw in (name, email, phone, str(message), source, page_url, language):
            if CONTROL_CHAR_RE.search(str(raw)):
                return False, 'INVALID_CHARACTERS', 422

        if not name:
            return False, 'NAME_REQUIRED', 422
        if len(name) > 150:
            return False, 'NAME_TOO_LONG', 422
        if not email and not phone:
            return False, 'CONTACT_REQUIRED', 422
        if email and not EMAIL_RE.match(email):
            return False, 'INVALID_EMAIL', 422
        if phone and len(phone) > 40:
            return False, 'PHONE_TOO_LONG', 422
        if message is not None and len(str(message)) > 5000:
            return False, 'MESSAGE_TOO_LONG', 422
        if source != 'perlavillalari.com':
            return False, 'INVALID_SOURCE', 422
        if page_url:
            try:
                parsed = urlparse(page_url)
            except Exception:
                return False, 'INVALID_PAGE_URL', 422
            if parsed.scheme not in ('http', 'https'):
                return False, 'INVALID_PAGE_URL', 422
            host = (parsed.hostname or '').lower()
            if host not in APPROVED_PAGE_HOSTS:
                return False, 'INVALID_PAGE_URL', 422
        if language and language not in ALLOWED_LANGUAGES:
            return False, 'INVALID_LANGUAGE', 422

        return True, None, 200

    def _resolve_assignment(self):
        """Resolve company/team/user/stage/source/type from trusted tenant params."""
        ICP = request.env['ir.config_parameter'].sudo()
        required = {
            'company': ICP.get_param('tcrm.public_lead.company'),
            'team': ICP.get_param('tcrm.public_lead.team'),
            'salesperson': ICP.get_param('tcrm.public_lead.salesperson'),
            'stage': ICP.get_param('tcrm.public_lead.stage'),
            'source': ICP.get_param('tcrm.public_lead.source'),
            'type': ICP.get_param('tcrm.public_lead.type') or 'opportunity',
        }
        for key, val in required.items():
            if key == 'type':
                continue
            if not (val or '').strip():
                return None, 'ASSIGNMENT_NOT_CONFIGURED'

        lead_type = (required['type'] or 'opportunity').strip()
        if lead_type not in ('lead', 'opportunity'):
            return None, 'ASSIGNMENT_NOT_CONFIGURED'

        company = self._resolve_record('res.company', required['company'])
        team = self._resolve_record('crm.team', required['team'])
        user = self._resolve_record('res.users', required['salesperson'])
        stage = self._resolve_record('crm.stage', required['stage'])
        source = self._resolve_record('utm.source', required['source'])

        if not all([company, team, user, stage, source]):
            return None, 'ASSIGNMENT_NOT_CONFIGURED'
        if not team.active:
            return None, 'ASSIGNMENT_NOT_CONFIGURED'
        if not user.active or user.share:
            return None, 'ASSIGNMENT_NOT_CONFIGURED'

        return {
            'company_id': company.id,
            'team_id': team.id,
            'user_id': user.id,
            'stage_id': stage.id,
            'source_id': source.id,
            'type': lead_type,
        }, None

    def _resolve_record(self, model, ref):
        """Resolve xmlid or positive integer id to a browse record."""
        ref = (ref or '').strip()
        if not ref:
            return None
        env = request.env[model].sudo()
        if '.' in ref and not ref.isdigit():
            try:
                return request.env.ref(ref)
            except Exception:
                return None
        if ref.isdigit():
            rec = env.browse(int(ref))
            return rec if rec.exists() else None
        # Name fallback (exact)
        return env.search([('name', '=', ref)], limit=1)

    def _create_lead(self, data, assignment, idempotency_key, raw_body_hash, correlation_id):
        lead_env = request.env['crm.lead'].sudo()
        name = (data.get('name') or '').strip()
        email = (data.get('email') or '').strip() or False
        phone = (data.get('phone') or '').strip() or False
        message = (data.get('message') or '')
        page_url = (data.get('page_url') or '').strip()
        language = (data.get('language') or '').strip().lower()

        description_parts = []
        if message:
            description_parts.append(str(message).strip())
        if page_url:
            description_parts.append(f'Page URL: {page_url}')
        if language:
            description_parts.append(f'Language: {language}')
        description_parts.append(f'Correlation-ID: {correlation_id}')

        vals = {
            'name': name,
            'contact_name': name,
            'email_from': email,
            'phone': phone,
            'description': '\n'.join(description_parts),
            'type': assignment['type'],
            'company_id': assignment['company_id'],
            'team_id': assignment['team_id'],
            'user_id': assignment['user_id'],
            'stage_id': assignment['stage_id'],
            'source_id': assignment['source_id'],
            'tcrm_idempotency_scope': IDEMPOTENCY_SCOPE,
            'tcrm_idempotency_key': idempotency_key,
            'tcrm_idempotency_payload_sha256': raw_body_hash,
            'tcrm_external_submission_id': idempotency_key,
        }

        try:
            with request.env.cr.savepoint():
                lead = lead_env.with_context(tcrm_integration_ingestion=True).create(vals)
            return lead, None, 200
        except IntegrityError as exc:
            pgcode = getattr(exc, 'pgcode', None)
            constraint_name = getattr(getattr(exc, 'diag', None), 'constraint_name', None)
            if pgcode != errorcodes.UNIQUE_VIOLATION or constraint_name not in (
                'unique_tcrm_lead_idempotency_scope_key',
                'crm_lead_unique_tcrm_lead_idempotency_scope_key',
            ):
                raise
            lead = lead_env.search([
                ('tcrm_idempotency_scope', '=', IDEMPOTENCY_SCOPE),
                ('tcrm_idempotency_key', '=', idempotency_key),
            ], limit=1)
            if not lead:
                raise
            if lead.tcrm_idempotency_payload_sha256 != raw_body_hash:
                return None, 'IDEMPOTENCY_PAYLOAD_MISMATCH', 409
            return lead, None, 200
