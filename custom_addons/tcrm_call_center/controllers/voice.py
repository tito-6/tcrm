# -*- coding: utf-8 -*-
"""Authenticated voice token + dialer helpers."""
from __future__ import annotations

import logging
import re

from tcrm import http, _
from tcrm.exceptions import AccessError, UserError
from tcrm.http import request

from ..services.crypto import mask_secret
from ..services.phone import mask_phone
from ..services.providers import get_provider
from ..services.rate_limit import allow as rate_allow

_logger = logging.getLogger(__name__)


def _ok(data=None):
    return {'ok': True, 'data': data if data is not None else {}}


def _err(message, *, code='error', status=400):
    return {'ok': False, 'error': {'code': code, 'message': str(message)}, 'status': status}


def _sanitize_identity(dbname: str, user_id: int) -> str:
    raw = 'tcrm_%s_u%s' % (dbname, user_id)
    return re.sub(r'[^A-Za-z0-9_]', '_', raw)[:120]


class SantralVoiceController(http.Controller):

    @http.route('/tcrm/voice/token', type='jsonrpc', auth='user', methods=['POST'])
    def voice_token(self, call_id=None, res_model=None, res_id=None, phone=None, **kwargs):
        env = request.env
        user = env.user
        if not user.has_group('tcrm_call_center.group_santral_user'):
            return _err(_('Santral Kullanıcısı yetkisi gerekli.'), code='access', status=403)

        db_key = 'token:%s:%s' % (env.cr.dbname, user.id)
        if not rate_allow(db_key, limit=30, window_seconds=60):
            return _err(_('Çok fazla token isteği. Lütfen bekleyin.'), code='rate_limit', status=429)

        config = env['tcrm.call.provider.config'].get_for_company(require_enabled=True)
        if not config:
            return _err(_('Santral yapılandırılmamış'), code='not_configured', status=400)

        Call = env['tcrm.call.record']
        dial_token = None
        call = Call.browse()
        if call_id:
            call = Call.browse(int(call_id))
            call.check_access('read')
            if not call.exists() or call.user_id.id != user.id:
                return _err(_('Çağrı kaydı erişilebilir değil.'), code='access', status=403)
            # Re-issue dial token only while still pending and unused.
            if call.status != 'pending' or call.dial_token_used:
                return _err(_('Arama yetkilendirmesi geçersiz.'), code='dial_auth', status=400)
            from ..services.dial_token import issue_dial_token
            import hashlib
            dial_token = issue_dial_token(
                env, call_id=call.id, destination=call.destination_number, user_id=user.id, ttl_seconds=120,
            )
            call.sudo().write({'dial_token_fingerprint': hashlib.sha256(dial_token.encode()).hexdigest()})
        else:
            if not res_model or not res_id:
                return _err(_('call_id veya CRM kaydı gerekli.'), code='validation', status=400)
            try:
                call, dial_token, config = Call.action_prepare_outbound(
                    res_model=res_model, res_id=int(res_id), phone=phone,
                )
            except (AccessError, UserError) as exc:
                return _err(exc, code='access' if isinstance(exc, AccessError) else 'error', status=403 if isinstance(exc, AccessError) else 400)

        identity = _sanitize_identity(env.cr.dbname, user.id)
        try:
            provider = get_provider(env, config)
            token_data = provider.create_access_token(identity=identity, ttl_seconds=300)
        except Exception as exc:
            _logger.warning('Santral token failed user=%s db=%s', user.id, env.cr.dbname)
            return _err(_('Token oluşturulamadı.'), code='token_error', status=500)

        # Response must never include secrets, auth token, or database name.
        return _ok({
            'access_token': token_data['token'],
            'expires_in': token_data.get('expires_in', 300),
            'ice_servers': token_data.get('ice_servers', []),
            'edge': config.twilio_edge or 'roaming',
            'call_id': call.id,
            'dial_token': dial_token,
            'caller_id_masked': mask_secret(call.caller_id, keep=4),
            'destination_masked': mask_phone(call.destination_number),
            'record_name': (call.lead_id or call.partner_id).display_name if (call.lead_id or call.partner_id) else call.display_name,
            'project_name': call.project_id.display_name if call.project_id else '',
            'recording_enabled': bool(config.recording_enabled),
        })

    @http.route('/tcrm/voice/call/<int:call_id>/wrapup', type='jsonrpc', auth='user', methods=['POST'])
    def call_wrapup(self, call_id, outcome=None, notes=None, create_followup=False,
                    followup_summary=None, followup_date=None, diagnostics=None, **kwargs):
        if not request.env.user.has_group('tcrm_call_center.group_santral_user'):
            return _err(_('Santral Kullanıcısı yetkisi gerekli.'), code='access', status=403)
        call = request.env['tcrm.call.record'].browse(int(call_id))
        call.check_access('write')
        if not call.exists():
            return _err(_('Çağrı bulunamadı.'), code='not_found', status=404)
            
        if diagnostics:
            call.sudo().write({
                'sdk_version': diagnostics.get('sdk_version'),
                'browser_os': diagnostics.get('browser_os'),
                'selected_edge': diagnostics.get('selected_edge'),
                'codec': diagnostics.get('codec'),
                'rtt': diagnostics.get('rtt'),
                'jitter': diagnostics.get('jitter'),
                'packet_loss': diagnostics.get('packet_loss'),
                'mos': diagnostics.get('mos'),
                'warning_events': diagnostics.get('warning_events'),
                'microphone_device': diagnostics.get('microphone_device'),
                'connection_type': diagnostics.get('connection_type'),
            })
            
        call.action_save_wrapup(
            outcome=outcome,
            notes=notes,
            create_followup=bool(create_followup),
            followup_summary=followup_summary,
            followup_date=followup_date,
        )
        return _ok({'call_id': call.id, 'outcome': call.outcome})

    @http.route('/tcrm/voice/call/<int:call_id>/status', type='jsonrpc', auth='user', methods=['POST'])
    def call_status_poll(self, call_id, **kwargs):
        if not request.env.user.has_group('tcrm_call_center.group_santral_user'):
            return _err(_('Santral Kullanıcısı yetkisi gerekli.'), code='access', status=403)
        call = request.env['tcrm.call.record'].browse(int(call_id))
        call.check_access('read')
        if not call.exists():
            return _err(_('Çağrı bulunamadı.'), code='not_found', status=404)
        return _ok({
            'call_id': call.id,
            'status': call.status,
            'duration': call.duration,
            'recording_state': call.recording_state,
            'recording_id': call.recording_ids[:1].id if call.recording_ids else False,
            'user_error_message': call.user_error_message or '',
            'provider_error_code': call.provider_error_code if request.env.user.has_group('tcrm_call_center.group_santral_admin') else '',
            'outcome': call.outcome,
            'notes': call.notes or '',
        })

    @http.route('/tcrm/voice/call/<int:call_id>/hangup', type='jsonrpc', auth='user', methods=['POST'])
    def call_hangup(self, call_id, **kwargs):
        if not request.env.user.has_group('tcrm_call_center.group_santral_user'):
            return _err(_('Santral Kullanıcısı yetkisi gerekli.'), code='access', status=403)
        call = request.env['tcrm.call.record'].browse(int(call_id))
        call.check_access('write')
        if not call.exists():
            return _err(_('Çağrı bulunamadı.'), code='not_found', status=404)
        call.action_hangup_local()
        return _ok({'call_id': call.id, 'status': call.status})

