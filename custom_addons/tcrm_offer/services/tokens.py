# -*- coding: utf-8 -*-
"""Token and passcode helpers for tcrm_offer."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import string


# Avoid ambiguous characters in passcodes
_PASSCODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generate_public_token() -> str:
    """≥128-bit entropy opaque URL token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str, *, pepper: str = '') -> str:
    """SHA-256 hash for public token lookup (with optional DB pepper)."""
    material = f'{pepper}:{token}'.encode('utf-8')
    return hashlib.sha256(material).hexdigest()


def generate_passcode(length: int = 7) -> str:
    length = max(6, min(8, int(length or 7)))
    return ''.join(secrets.choice(_PASSCODE_ALPHABET) for _ in range(length))


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a or '', b or '')


def mask_ip(ip: str | None) -> str:
    if not ip:
        return ''
    parts = ip.split('.')
    if len(parts) == 4:
        return f'{parts[0]}.{parts[1]}.x.x'
    if ':' in ip:
        # IPv6 — keep first two hextets
        hextets = ip.split(':')
        return ':'.join(hextets[:2] + ['xxxx'])
    return 'x'


def snapshot_checksum(payload: str) -> str:
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()
