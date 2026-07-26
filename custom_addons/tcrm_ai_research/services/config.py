# Part of TCRM AI Research. See LICENSE for details.
"""Secure configuration loader for RAGFlow (ICP + optional env overrides)."""

from __future__ import annotations

import os
from typing import Any

# Environment variables may override sensitive / deployment-specific values.
_ENV_MAP = {
    'base_url': 'RAGFLOW_BASE_URL',
    'api_key': 'RAGFLOW_API_KEY',
    'default_dataset_id': 'RAGFLOW_DEFAULT_DATASET_ID',
    'default_assistant_id': 'RAGFLOW_DEFAULT_ASSISTANT_ID',
    'timeout': 'RAGFLOW_TIMEOUT',
}

_ICP_PREFIX = 'tcrm_ai_research.'


def _env_or_icp(env, key: str, default: str = '') -> str:
    env_name = _ENV_MAP.get(key)
    if env_name:
        value = os.environ.get(env_name)
        if value is not None and str(value).strip() != '':
            return str(value).strip()
    ICP = env['ir.config_parameter'].sudo()
    return (ICP.get_param(f'{_ICP_PREFIX}{key}', default) or default).strip()


def get_ragflow_config(env) -> dict[str, Any]:
    """Return sanitized RAGFlow config. Never log the API key."""
    timeout_raw = _env_or_icp(env, 'timeout', '60')
    try:
        timeout = max(5, min(300, int(timeout_raw)))
    except (TypeError, ValueError):
        timeout = 60

    max_upload_raw = env['ir.config_parameter'].sudo().get_param(
        f'{_ICP_PREFIX}max_upload_size_mb', '25'
    )
    try:
        max_upload_mb = max(1, min(200, int(max_upload_raw)))
    except (TypeError, ValueError):
        max_upload_mb = 25

    allowed = env['ir.config_parameter'].sudo().get_param(
        f'{_ICP_PREFIX}allowed_extensions',
        'pdf,txt,doc,docx,md,csv,xlsx,pptx',
    ) or 'pdf,txt,doc,docx,md,csv,xlsx,pptx'
    extensions = {
        ext.strip().lower().lstrip('.')
        for ext in allowed.split(',')
        if ext.strip()
    }

    streaming = env['ir.config_parameter'].sudo().get_param(
        f'{_ICP_PREFIX}enable_streaming', 'True'
    ) == 'True'
    web_research = env['ir.config_parameter'].sudo().get_param(
        f'{_ICP_PREFIX}enable_web_research', 'False'
    ) == 'True'
    language = env['ir.config_parameter'].sudo().get_param(
        f'{_ICP_PREFIX}default_language', 'tr'
    ) or 'tr'

    return {
        'base_url': _env_or_icp(env, 'base_url', '').rstrip('/'),
        'api_key': _env_or_icp(env, 'api_key', ''),
        'default_dataset_id': _env_or_icp(env, 'default_dataset_id', ''),
        'default_assistant_id': _env_or_icp(env, 'default_assistant_id', ''),
        'timeout': timeout,
        'max_upload_size_mb': max_upload_mb,
        'max_upload_size_bytes': max_upload_mb * 1024 * 1024,
        'allowed_extensions': extensions,
        'enable_streaming': streaming,
        'enable_web_research': web_research,
        'default_language': language if language in ('tr', 'en') else 'tr',
    }


def public_config_dict(env) -> dict[str, Any]:
    """Config safe to return to the browser (no secrets)."""
    cfg = get_ragflow_config(env)
    return {
        'default_language': cfg['default_language'],
        'enable_streaming': cfg['enable_streaming'],
        'enable_web_research': cfg['enable_web_research'],
        'max_upload_size_mb': cfg['max_upload_size_mb'],
        'allowed_extensions': sorted(cfg['allowed_extensions']),
        'configured': bool(cfg['base_url'] and cfg['api_key']),
    }
