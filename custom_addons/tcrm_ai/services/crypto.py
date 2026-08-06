# Part of TCRM AI. See LICENSE for details.
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
        secret = 'tcrm-ai:%s' % env.cr.dbname
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
        _logger.warning('TCRM AI: failed to decrypt secret in db=%s', env.cr.dbname)
        return ''


def mask_api_key(value: str | None, keep: int = 4) -> str:
    """Return masked display like gsk_••••••••••••1234."""
    if not value:
        return ''
    text = str(value)
    if text.startswith(ENC_PREFIX):
        return '••••••••'
    prefix = ''
    body = text
    if text.startswith('gsk_'):
        prefix = 'gsk_'
        body = text[4:]
    elif '_' in text[:8]:
        idx = text.find('_')
        prefix = text[: idx + 1]
        body = text[idx + 1:]
    if len(body) <= keep:
        return prefix + ('•' * max(4, len(body)))
    return prefix + ('•' * max(8, len(body) - keep)) + body[-keep:]


def mask_secret(value: str | None, keep: int = 4) -> str:
    if not value:
        return ''
    text = str(value)
    if len(text) <= keep:
        return '•' * len(text)
    return ('•' * (len(text) - keep)) + text[-keep:]


def looks_like_masked_secret(value: str | None) -> bool:
    """True for UI placeholders / masked keys that must never be stored or sent."""
    if not value:
        return False
    text = str(value).strip()
    if not text:
        return False
    if any(ch in text for ch in ('•', '●', '▪', '▫', '·')):
        return True
    if set(text) <= {'*', '•', '.', 'x', 'X', '-'}:
        return True
    if '****' in text or '••••' in text:
        return True
    return False


def normalize_api_key(value: str | None) -> str:
    """Return a latin-1-safe API key, or '' if empty/masked/invalid."""
    if not value:
        return ''
    text = str(value).strip().replace('\u200b', '').replace('\ufeff', '')
    if not text or looks_like_masked_secret(text):
        return ''
    # HTTP Authorization headers must be latin-1 / ASCII.
    try:
        text.encode('ascii')
    except UnicodeEncodeError:
        return ''
    return text
