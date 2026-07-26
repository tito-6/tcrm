# -*- coding: utf-8 -*-
"""Tenant-local secret encryption helpers (Fernet over database.secret)."""
from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

_logger = logging.getLogger(__name__)

ENC_PREFIX = 'enc:v1:'


def _fernet(env) -> Fernet:
    secret = env['ir.config_parameter'].sudo().get_param('database.secret') or ''
    if not secret:
        # Fallback must still be DB-bound so values cannot be decrypted cross-DB.
        secret = 'tcrm-call-center:%s' % env.cr.dbname
    digest = hashlib.sha256(secret.encode('utf-8')).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(env, plaintext: str | None) -> str:
    if not plaintext:
        return ''
    if str(plaintext).startswith(ENC_PREFIX):
        return str(plaintext)
    token = _fernet(env).encrypt(str(plaintext).encode('utf-8')).decode('ascii')
    return ENC_PREFIX + token


def decrypt_secret(env, stored: str | None) -> str:
    if not stored:
        return ''
    value = str(stored)
    if not value.startswith(ENC_PREFIX):
        # Legacy / plaintext transitional value — never log it.
        return value
    token = value[len(ENC_PREFIX):]
    try:
        return _fernet(env).decrypt(token.encode('ascii')).decode('utf-8')
    except InvalidToken:
        _logger.warning('Santral: failed to decrypt secret in db=%s', env.cr.dbname)
        return ''


def mask_secret(value: str | None, keep: int = 4) -> str:
    if not value:
        return ''
    text = str(value)
    if len(text) <= keep:
        return '*' * len(text)
    return ('*' * (len(text) - keep)) + text[-keep:]


def mask_sid(value: str | None, keep_prefix: int = 2, keep_suffix: int = 4) -> str:
    if not value:
        return ''
    text = str(value)
    if len(text) <= keep_prefix + keep_suffix:
        return mask_secret(text, keep=2)
    return text[:keep_prefix] + ('*' * (len(text) - keep_prefix - keep_suffix)) + text[-keep_suffix:]
