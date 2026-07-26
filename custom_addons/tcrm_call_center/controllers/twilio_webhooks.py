# -*- coding: utf-8 -*-
"""Twilio voice/recording webhooks (signature-validated, tenant-local)."""
from __future__ import annotations

import logging
from datetime import timedelta

from tcrm import http, fields
from tcrm.http import request
from werkzeug.wrappers import Response

from ..services.dial_token import validate_dial_token
from ..services.phone import mask_phone
from ..services.providers import get_provider

_logger = logging.getLogger(__name__)


def _twiml_error(message: str) -> Response:
    xml = '<?xml version="1.0" encoding="UTF-8"?><Response><Say language="tr-TR">%s</Say><Hangup/></Response>' % (
        message.replace('&', 've').replace('<', '').replace('>', '')
    )
    return Response(xml, status=200, mimetype='text/xml')


def _empty_ok() -> Response:
    return Response('<?xml version="1.0" encoding="UTF-8"?><Response></Response>', status=200, mimetype='text/xml')


def _form_params():
    return {k: v for k, v in request.httprequest.form.items()}


def _public_url(config, path: str) -> str:
    base = config.get_public_callback_base()
    if not base:
        # Reconstruct from request only as last resort; prefer configured base.
        base = request.httprequest.url_root.rstrip('/')
        if request.httprequest.headers.get('X-Forwarded-Proto') == 'https':
            base = 'https://' + request.httprequest.host
    return base.rstrip('/') + path


def _validate_signature(config, path: str) -> bool:
    signature = request.httprequest.headers.get('X-Twilio-Signature', '')
    url = _public_url(config, path)
    # Twilio signs the exact public URL. Also try the reconstructed request URL.
    provider = get_provider(request.env, config)
    params = _form_params()
    if provider.validate_webhook_signature(url, params, signature):
        return True
    # Alternate: url_root + path (proxy_mode aware via werkzeug)
    alt = request.httprequest.url
    if alt and provider.validate_webhook_signature(alt, params, signature):
        return True
    return False


class SantralTwilioWebhookController(http.Controller):

    @http.route(
        '/tcrm/twilio/voice/outgoing',
        type='http', auth='public', methods=['POST'], csrf=False,
    )
    def voice_outgoing(self, **kwargs):
        env = request.env
        params = _form_params()
        config = env['tcrm.call.provider.config'].sudo().get_for_company(env.company, require_enabled=True)
        if not config:
            # Multi-company: try any enabled config matching AccountSid.
            account_sid = params.get('AccountSid')
            config = env['tcrm.call.provider.config'].sudo().search([
                ('enabled', '=', True),
                ('account_sid', '=', account_sid),
            ], limit=1)
        if not config or not config.enabled:
            _logger.warning('Santral outgoing: no enabled config db=%s', env.cr.dbname)
            return _twiml_error('Santral yapilandirilmamis')

        if not _validate_signature(config, '/tcrm/twilio/voice/outgoing'):
            _logger.warning('Santral outgoing: invalid signature db=%s', env.cr.dbname)
            return Response('Forbidden', status=403)

        call_id = params.get('callId') or params.get('CallId')
        dial_token = params.get('dialToken') or params.get('DialToken')
        call_sid = params.get('CallSid')
        try:
            call = env['tcrm.call.record'].sudo().browse(int(call_id))
        except Exception:
            return _twiml_error('Gecersiz arama')

        if not call.exists() or call.company_id.id != config.company_id.id:
            return _twiml_error('Gecersiz arama')
        if call.dial_token_used:
            return _twiml_error('Yetki kullanildi')
        if not validate_dial_token(
            env, dial_token,
            call_id=call.id,
            destination=call.destination_number,
            user_id=call.user_id.id,
        ):
            return _twiml_error('Yetki gecersiz')

        # Destination is locked on the pending record — never accept To from browser.
        to_number = call.destination_number
        from_number = config.verified_caller_id

        import re
        if not from_number or not re.match(r'^\+[1-9]\d{1,14}$', from_number):
            _logger.warning('Santral outgoing: invalid or missing caller id db=%s caller_id=%s', env.cr.dbname, from_number)
            return _twiml_error('Geçerli arayan numarası yapılandırılmamış.')

        status_cb = _public_url(config, '/tcrm/twilio/call/status')
        recording_cb = _public_url(config, '/tcrm/twilio/recording/status')
        provider = get_provider(env, config)
        twiml = provider.build_outgoing_twiml(
            to_number=to_number,
            from_number=from_number,
            call_record=call,
            status_callback=status_cb,
            recording_callback=recording_cb,
        )
        call.write({
            'provider_call_sid': call_sid or call.provider_call_sid,
            'dial_token_used': True,
            'status': 'initiated',
            'caller_id': from_number,
        })
        
        # Mask numbers in logged TwiML
        masked_twiml = twiml.replace(to_number, mask_phone(to_number)).replace(from_number, mask_phone(from_number))
        
        _logger.info(
            'Santral outgoing ok call_id=%s dest=%s db=%s twiml=%s',
            call.id, mask_phone(to_number), env.cr.dbname, masked_twiml
        )
        return Response(twiml, status=200, mimetype='text/xml')

    @http.route(
        '/tcrm/twilio/call/status',
        type='http', auth='public', methods=['POST'], csrf=False,
    )
    def call_status(self, **kwargs):
        env = request.env
        params = _form_params()
        account_sid = params.get('AccountSid')
        config = env['tcrm.call.provider.config'].sudo().search([
            ('account_sid', '=', account_sid),
            ('enabled', '=', True),
        ], limit=1)
        if not config:
            config = env['tcrm.call.provider.config'].sudo().get_for_company(env.company)
        if not config:
            return Response('OK', status=200)
        if not _validate_signature(config, '/tcrm/twilio/call/status'):
            _logger.warning('Santral call status: invalid signature db=%s', env.cr.dbname)
            return Response('Forbidden', status=403)

        call_sid = params.get('CallSid')
        parent_sid = params.get('ParentCallSid')
        call_status = params.get('CallStatus')
        duration = params.get('CallDuration') or params.get('Duration')
        error_code = params.get('ErrorCode')
        error_message = params.get('ErrorMessage')
        timestamp = params.get('Timestamp')

        Call = env['tcrm.call.record'].sudo()
        call = Call.search([
            '|', ('provider_call_sid', '=', call_sid),
            '|', ('parent_call_sid', '=', call_sid),
            ('provider_call_sid', '=', parent_sid),
        ], limit=1)
        if not call and params.get('callId'):
            call = Call.browse(int(params.get('callId')))

        safe_payload = {
            'CallStatus': call_status,
            'CallSid': call_sid,
            'ParentCallSid': parent_sid,
            'CallDuration': duration,
            'ErrorCode': error_code,
            # Intentionally omit full To/From
            'ToMasked': mask_phone(params.get('To')),
            'FromMasked': mask_phone(params.get('From')),
        }
        event, duplicate = env['tcrm.call.webhook.event'].register_or_skip(
            company=config.company_id,
            call=call,
            event_type='call_status',
            provider_sid=call_sid,
            status=call_status,
            timestamp=timestamp or '',
            safe_payload=safe_payload,
        )
        if duplicate:
            return Response('OK', status=200)

        if call and call.exists():
            call._apply_status_event(
                call_status=call_status,
                call_sid=call_sid,
                parent_sid=parent_sid,
                duration=duration,
                error_code=error_code,
                error_message=error_message,
            )
        event.write({'processed': True, 'processed_at': fields.Datetime.now()})
        return Response('OK', status=200)

    @http.route(
        '/tcrm/twilio/recording/status',
        type='http', auth='public', methods=['POST'], csrf=False,
    )
    def recording_status(self, **kwargs):
        env = request.env
        params = _form_params()
        account_sid = params.get('AccountSid')
        config = env['tcrm.call.provider.config'].sudo().search([
            ('account_sid', '=', account_sid),
        ], limit=1)
        if not config:
            return Response('OK', status=200)
        if account_sid and config.account_sid and account_sid != config.account_sid:
            return Response('Forbidden', status=403)
        if not _validate_signature(config, '/tcrm/twilio/recording/status'):
            _logger.warning('Santral recording status: invalid signature db=%s', env.cr.dbname)
            return Response('Forbidden', status=403)

        recording_sid = params.get('RecordingSid')
        call_sid = params.get('CallSid')
        status = (params.get('RecordingStatus') or '').lower()
        duration = int(params.get('RecordingDuration') or 0)
        channels = int(params.get('RecordingChannels') or 0)

        Call = env['tcrm.call.record'].sudo()
        call = Call.search([
            '|', ('provider_call_sid', '=', call_sid),
            ('parent_call_sid', '=', call_sid),
        ], limit=1)
        safe_payload = {
            'RecordingSid': recording_sid,
            'RecordingStatus': status,
            'RecordingDuration': duration,
            'RecordingChannels': channels,
            'CallSid': call_sid,
        }
        event, duplicate = env['tcrm.call.webhook.event'].register_or_skip(
            company=config.company_id,
            call=call,
            event_type='recording_status',
            provider_sid=recording_sid,
            status=status,
            timestamp=params.get('Timestamp') or '',
            safe_payload=safe_payload,
        )
        if duplicate:
            return Response('OK', status=200)

        if call and call.exists() and recording_sid:
            Recording = env['tcrm.call.recording'].sudo()
            rec = Recording.search([('recording_sid', '=', recording_sid)], limit=1)
            retention = False
            if config.recording_retention_days:
                retention = fields.Date.to_date(fields.Date.context_today(env.user)) + timedelta(
                    days=int(config.recording_retention_days)
                )
            vals = {
                'name': 'REC %s' % recording_sid,
                'company_id': config.company_id.id,
                'call_id': call.id,
                'provider': 'twilio',
                'recording_sid': recording_sid,
                'status': 'completed' if status == 'completed' else ('failed' if status == 'failed' else 'processing'),
                'duration': duration,
                'channels': channels,
                'retention_deadline': retention,
            }
            if rec:
                rec.write(vals)
            else:
                rec = Recording.create(vals)
            call.write({
                'recording_sid': recording_sid,
                'recording_duration': duration,
                'recording_channels': channels,
                'recording_state': 'ready' if status == 'completed' else ('failed' if status == 'failed' else 'pending'),
            })
            if status == 'completed' and config.recording_storage == 'attachment':
                try:
                    rec.server_store_from_provider()
                except Exception:
                    _logger.warning('Santral recording fetch deferred recording=%s', recording_sid)
        event.write({'processed': True, 'processed_at': fields.Datetime.now()})
        return Response('OK', status=200)
