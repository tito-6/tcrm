# -*- coding: utf-8 -*-
"""Phone normalization and destination policy checks."""
from __future__ import annotations

import re

from tcrm.exceptions import UserError

# Turkish mobile / landline rough patterns after E.164 normalization.
_E164_RE = re.compile(r'^\+[1-9]\d{7,14}$')

# Shared / premium / special ranges we refuse for outbound browser dialing.
_DISALLOWED_PREFIXES = (
    '+1900', '+1976', '+1449', '+1809', '+1829', '+1849',  # common premium/shared
    '+44870', '+44871', '+449', '+900',
)


def digits_only(value: str | None) -> str:
    return re.sub(r'\D+', '', value or '')


def normalize_e164(raw: str | None, default_country: str = 'TR') -> str:
    """Normalize to E.164. Default country TR for local 0xxxxxxxxxx numbers."""
    if not raw:
        raise UserError('Geçersiz telefon numarası.')
    text = str(raw).strip()
    if text.startswith('00'):
        text = '+' + text[2:]
    if text.startswith('+'):
        candidate = '+' + digits_only(text)
    else:
        digits = digits_only(text)
        if default_country == 'TR':
            if digits.startswith('90') and len(digits) >= 12:
                candidate = '+' + digits
            elif digits.startswith('0') and len(digits) == 11:
                candidate = '+90' + digits[1:]
            elif len(digits) == 10:
                candidate = '+90' + digits
            else:
                candidate = '+' + digits
        else:
            candidate = '+' + digits
    if not _E164_RE.match(candidate):
        raise UserError('Telefon numarası E.164 formatında değil.')
    return candidate


def mask_phone(e164: str | None) -> str:
    if not e164:
        return ''
    digits = digits_only(e164)
    if len(digits) <= 4:
        return '*' * len(digits)
    return ('*' * (len(digits) - 4)) + digits[-4:]


def assert_allowed_destination(e164: str) -> None:
    if not e164 or not _E164_RE.match(e164):
        raise UserError('Geçersiz hedef numara.')
    for prefix in _DISALLOWED_PREFIXES:
        if e164.startswith(prefix):
            raise UserError('Bu numara türüne arama yapılamaz.')
    # Extremely short / long already rejected by E.164 regex.
    if e164.startswith('+90') and len(digits_only(e164)) not in (12,):
        # TR E.164 is +90 + 10 digits = 12 digit body
        if len(digits_only(e164)) < 11:
            raise UserError('Türkiye numarası geçersiz.')
