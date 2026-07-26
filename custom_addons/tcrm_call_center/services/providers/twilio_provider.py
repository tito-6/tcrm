# -*- coding: utf-8 -*-
"""Twilio Voice provider adapter (outbound browser calling)."""
from __future__ import annotations

import logging
from urllib.parse import urljoin

import requests
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

from ..crypto import decrypt_secret
from .base import CallProviderBase

_logger = logging.getLogger(__name__)


class TwilioCallProvider(CallProviderBase):
    name = 'twilio'

    def _account_sid(self) -> str:
        return (self.config.account_sid or '').strip()

    def _api_key_sid(self) -> str:
        return (self.config.api_key_sid or '').strip()

    def _api_key_secret(self) -> str:
        return decrypt_secret(self.env, self.config.api_key_secret_encrypted)

    def _auth_token(self) -> str:
        return decrypt_secret(self.env, self.config.auth_token_encrypted)

    def _twiml_app_sid(self) -> str:
        return (self.config.twiml_app_sid or '').strip()

    def _client(self) -> Client:
        account = self._account_sid()
        key = self._api_key_sid()
        secret = self._api_key_secret()
        token = self._auth_token()
        # Try API Key auth first; fall back to Auth Token on failure.
        if account and key and secret:
            try:
                client = Client(key, secret, account_sid=account)
                # Verify the client works by fetching the account.
                client.api.accounts(account).fetch()
                return client
            except Exception as exc:
                err_msg = str(exc).lower()
                if '401' in err_msg or 'authenticate' in err_msg:
                    _logger.warning(
                        'Santral: API Key auth failed (401), falling back to Auth Token'
                    )
                else:
                    raise
        if account and token:
            return Client(account, token)
        raise ValueError('Santral yapılandırılmamış')

    def test_connection(self) -> dict:
        client = self._client()
        account_sid = self._account_sid()
        try:
            account = client.api.accounts(account_sid).fetch()
        except Exception:
            # _client() may have already validated; re-fetch for test result.
            account = client.api.accounts(account_sid).fetch()
        # Determine which auth method succeeded.
        auth_method = 'Auth Token'
        key = self._api_key_sid()
        secret = self._api_key_secret()
        if key and secret and client.username == key:
            auth_method = 'API Key'
        # Do not log full Twilio payloads.
        return {
            'ok': True,
            'account_status': getattr(account, 'status', '') or '',
            'friendly_name': getattr(account, 'friendly_name', '') or '',
            'message': 'Twilio bağlantısı başarılı (%s)' % auth_method,
        }

    def create_access_token(self, *, identity: str, ttl_seconds: int = 300) -> dict:
        account_sid = self._account_sid()
        api_key = self._api_key_sid()
        api_secret = self._api_key_secret()
        app_sid = self._twiml_app_sid()
        if not all([account_sid, api_key, api_secret, app_sid]):
            raise ValueError('Santral yapılandırılmamış')
        token = AccessToken(account_sid, api_key, api_secret, identity=identity, ttl=ttl_seconds)
        grant = VoiceGrant(outgoing_application_sid=app_sid, incoming_allow=False)
        token.add_grant(grant)
        jwt = token.to_jwt()
        if isinstance(jwt, bytes):
            jwt = jwt.decode('utf-8')

        ice_servers = []
        try:
            client = self._client()
            nts = client.tokens.create(ttl=ttl_seconds)
            ice_servers = nts.ice_servers
        except Exception as exc:
            _logger.warning('Failed to fetch Twilio ICE servers: %s', exc)

        return {
            'token': jwt,
            'identity': identity,
            'expires_in': ttl_seconds,
            'ice_servers': ice_servers,
        }

    def build_outgoing_twiml(self, *, to_number: str, from_number: str, call_record, status_callback: str, recording_callback: str) -> str:
        response = VoiceResponse()
        if self.config.recording_enabled and self.config.recording_announcement_enabled:
            text = (self.config.recording_announcement_text or '').strip()
            if text:
                response.say(text, language='tr-TR')

        dial_kwargs = {
            'callerId': from_number,
            'answerOnBridge': True,
            'action': status_callback,
            'method': 'POST',
        }
        if self.config.recording_enabled:
            dial_kwargs.update({
                'record': 'record-from-answer-dual' if self.config.dual_channel_recording else 'record-from-answer',
                'recordingStatusCallback': recording_callback,
                'recordingStatusCallbackMethod': 'POST',
                'recordingStatusCallbackEvent': 'completed absent',
            })
        dial = response.dial(**dial_kwargs)
        dial.number(
            to_number,
            status_callback=status_callback,
            status_callback_method='POST',
            status_callback_event='initiated ringing answered completed',
        )
        return str(response)

    def validate_webhook_signature(self, url: str, params: dict, signature: str) -> bool:
        token = self._auth_token()
        if not token or not signature:
            return False
        validator = RequestValidator(token)
        return bool(validator.validate(url, params, signature))

    def fetch_recording_bytes(self, recording_sid: str) -> tuple[bytes, str]:
        account = self._account_sid()
        token = self._auth_token()
        if not account or not token or not recording_sid:
            raise ValueError('Recording unavailable')
        # Prefer media URL via REST; avoid exposing unrestricted URL to browser.
        url = 'https://api.twilio.com/2010-04-01/Accounts/%s/Recordings/%s.mp3' % (
            account, recording_sid,
        )
        resp = requests.get(url, auth=(account, token), timeout=60)
        if resp.status_code >= 400:
            # Fallback wav
            url = url[:-4] + '.wav'
            resp = requests.get(url, auth=(account, token), timeout=60)
        resp.raise_for_status()
        ctype = resp.headers.get('Content-Type') or 'audio/mpeg'
        return resp.content, ctype

    def map_trial_error(self, error_code, error_message: str | None) -> str:
        code = str(error_code or '')
        msg = (error_message or '').lower()
        if code in ('21219', '21214', '21215', '21216', '21217') or 'unverified' in msg or 'trial' in msg:
            return 'Twilio deneme hesabı yalnızca doğrulanmış numaraları arayabilir.'
        if code in ('31005', '32009', '32102', '32205'):
            return 'Twilio, Türkiye aramalarında Türk caller ID kullanımına izin vermedi.'
        return ''
