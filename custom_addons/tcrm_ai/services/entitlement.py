# Part of TCRM AI. See LICENSE for details.
"""Local entitlement gate for the current database (master or tenant)."""
from __future__ import annotations

from tcrm import _

from .constants import (
    ENTITLEMENT_PARAM,
    SAFE_ERROR_CODES,
    SUSPENDED_PARAM,
)


def _icp(env):
    return env['ir.config_parameter'].sudo()


def is_master_database(env) -> bool:
    """True when current DB is the SaaS control database."""
    from tcrm.tools import config

    control_db = (config.get('tcrm_control_db') or 'tcrm_master').strip()
    if env.cr.dbname == control_db:
        return True
    # Fallback for older installs that still host the tenant model only on master.
    return 'tcrm.tenant' in env and env.cr.dbname in (control_db, 'tcrm_master')


def get_entitlement_state(env) -> str:
    """Return local entitlement state for the current database."""
    if is_master_database(env):
        # Master/control DB always has local AI access for system admins.
        # Prefer stored state, but never leave master permanently stuck on
        # config_required when a working key + successful connection exist.
        state = (_icp(env).get_param(ENTITLEMENT_PARAM) or 'active').strip()
        return state or 'active'
    state = (_icp(env).get_param(ENTITLEMENT_PARAM) or 'unavailable').strip()
    if _icp(env).get_param(SUSPENDED_PARAM) == '1' and state not in ('unavailable', 'suspended'):
        return 'suspended'
    return state or 'unavailable'


def set_entitlement_state(env, state: str) -> None:
    _icp(env).set_param(ENTITLEMENT_PARAM, state)
    if state == 'suspended':
        _icp(env).set_param(SUSPENDED_PARAM, '1')
    elif state in ('granted', 'config_required', 'active', 'unavailable'):
        _icp(env).set_param(SUSPENDED_PARAM, '0')


def entitlement_allows_requests(env) -> tuple[bool, str | None]:
    """
    Return (ok, safe_error_code).
    Blocks when entitlement missing/suspended/unavailable.
    """
    state = get_entitlement_state(env)
    if state in ('unavailable',):
        return False, 'entitlement_denied'
    if state == 'suspended':
        return False, 'suspended'
    if state == 'quota_exceeded':
        return False, 'quota_exceeded'
    # granted / config_required / active / connection_error may proceed to config checks
    return True, None


def chat_block_reason(env) -> str | None:
    """Human-readable Turkish reason when chat must be disabled, else None."""
    ok, code = entitlement_allows_requests(env)
    if not ok:
        return SAFE_ERROR_CODES.get(code or 'entitlement_denied')
    Config = env['tcrm.ai.config']
    config = Config.sudo().get_config()
    if not config.ai_enabled:
        return 'TCRM AI devre dışı bırakıldı.'
    if not config.has_api_key:
        return SAFE_ERROR_CODES['config_missing']
    # config_required only blocks when setup is still incomplete.
    if config.entitlement_status == 'config_required' and config.last_connection_status != 'ok':
        return 'Yapılandırma gerekli — Ayarlardan API anahtarını kaydedip Bağlantıyı Test Et.'
    if config.last_connection_status == 'error' and config.entitlement_status == 'connection_error':
        return SAFE_ERROR_CODES.get('unreachable') or 'Bağlantı hatası — ayarlardan testi tekrarlayın.'
    return None


def ensure_request_allowed(env) -> None:
    from tcrm.exceptions import AccessError, UserError

    ok, code = entitlement_allows_requests(env)
    if not ok:
        raise AccessError(SAFE_ERROR_CODES.get(code or 'entitlement_denied'))
    config = env['tcrm.ai.config'].sudo().get_config()
    if not config.ai_enabled:
        raise UserError(_('TCRM AI devre dışı bırakıldı.'))
    if not config.has_api_key:
        raise UserError(SAFE_ERROR_CODES['config_missing'])
