# -*- coding: utf-8 -*-
"""Pure, dependency-free helpers for tenant provisioning.

Kept free of Odoo ORM imports so they can be unit-tested in isolation and reused
by the standalone privileged worker.
"""
import hashlib
import hmac
import re

# A database name must be a safe PostgreSQL identifier we fully control:
#   * starts with a lowercase letter,
#   * only lowercase letters, digits, underscores,
#   * length 3..63 (PostgreSQL identifier limit is 63).
# No hyphens, dots, spaces, quotes -> safe to embed in CREATE DATABASE "<name>".
DB_NAME_RE = re.compile(r'^[a-z][a-z0-9_]{2,62}$')

# Module names installable by the worker must match the Odoo module convention.
MODULE_NAME_RE = re.compile(r'^[a-z0-9_]+$')

# Names that must never be used as a tenant database.
RESERVED_DB_NAMES = frozenset({
    'postgres', 'template0', 'template1',
    'tcrm_master', 'odoo', 'master', 'control', 'public',
})


def is_valid_db_name(name):
    """True if *name* is a syntactically safe, non-reserved tenant DB name."""
    if not name or not isinstance(name, str):
        return False
    if not DB_NAME_RE.match(name):
        return False
    if name in RESERVED_DB_NAMES:
        return False
    return True


def validate_db_name(name):
    """Return *name* if valid, else raise ValueError with a clear reason."""
    if not name or not isinstance(name, str):
        raise ValueError('Database name is required.')
    if not DB_NAME_RE.match(name):
        raise ValueError(
            'Invalid database name %r: use 3-63 chars, start with a lowercase '
            'letter, only lowercase letters, digits and underscores (no hyphens/'
            'spaces/dots).' % (name,)
        )
    if name in RESERVED_DB_NAMES:
        raise ValueError('Database name %r is reserved.' % (name,))
    return name


def parse_module_set(module_csv):
    """Parse a comma/space separated module list into a validated, de-duplicated,
    order-preserving list. Rejects any token that is not a valid module name."""
    if not module_csv:
        raise ValueError('Empty module set.')
    raw = [m.strip() for m in re.split(r'[,\s]+', module_csv) if m.strip()]
    seen = set()
    out = []
    for m in raw:
        if not MODULE_NAME_RE.match(m):
            raise ValueError('Invalid module name in module set: %r' % (m,))
        if m not in seen:
            seen.add(m)
            out.append(m)
    if not out:
        raise ValueError('Module set resolved to an empty list.')
    return out


def sign_job(secret, tenant_id, db_name, nonce):
    """Deterministic HMAC-SHA256 signature binding a job to its tenant+db+nonce.

    Proves the job was minted by the control plane (which alone knows *secret*),
    so the worker can refuse to act on forged/tampered rows."""
    if not secret:
        raise ValueError('Missing signing secret.')
    payload = ('%s|%s|%s' % (tenant_id, db_name or '', nonce)).encode('utf-8')
    return hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()


def verify_job(secret, token, tenant_id, db_name, nonce):
    """Constant-time verification of a job token."""
    if not token:
        return False
    try:
        expected = sign_job(secret, tenant_id, db_name, nonce)
    except ValueError:
        return False
    return hmac.compare_digest(expected, token)


# Modules whose owner-level credentials must NEVER be copied into a tenant DB.
# The worker asserts these config models are empty in a freshly provisioned tenant.
SENSITIVE_CREDENTIAL_CHECKS = (
    # (model, [fields that must be empty/false in a new tenant])
    ('tcrm.call.provider.config', ['account_sid', 'auth_token_encrypted',
                                   'api_key_sid', 'api_key_secret_encrypted']),
)
