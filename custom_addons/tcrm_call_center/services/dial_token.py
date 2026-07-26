# -*- coding: utf-8 -*-
"""Signed one-time dial authorization (HMAC, short-lived)."""
from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode


def _signing_key(env) -> bytes:
    secret = env['ir.config_parameter'].sudo().get_param('database.secret') or ''
    material = 'tcrm-call-dial:%s:%s' % (env.cr.dbname, secret)
    return hashlib.sha256(material.encode('utf-8')).digest()


def issue_dial_token(env, *, call_id: int, destination: str, user_id: int, ttl_seconds: int = 120) -> str:
    exp = int(time.time()) + int(ttl_seconds)
    payload = 'v1|%s|%s|%s|%s' % (call_id, destination, user_id, exp)
    sig = hmac.new(_signing_key(env), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return '%s.%s' % (payload, sig)


def validate_dial_token(env, token: str, *, call_id: int, destination: str, user_id: int | None = None) -> bool:
    if not token or '.' not in token:
        return False
    payload, sig = token.rsplit('.', 1)
    expected = hmac.new(_signing_key(env), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return False
    parts = payload.split('|')
    if len(parts) != 5 or parts[0] != 'v1':
        return False
    try:
        tok_call = int(parts[1])
        tok_dest = parts[2]
        tok_user = int(parts[3])
        exp = int(parts[4])
    except (TypeError, ValueError):
        return False
    if tok_call != int(call_id):
        return False
    if tok_dest != destination:
        return False
    if user_id is not None and tok_user != int(user_id):
        return False
    if exp < int(time.time()):
        return False
    return True


def dial_params_for_sdk(call_id: int, dial_token: str) -> dict:
    """Params the browser SDK must pass as custom Twilio params."""
    return {
        'callId': str(call_id),
        'dialToken': dial_token,
    }


def encode_query(params: dict) -> str:
    return urlencode(params)
