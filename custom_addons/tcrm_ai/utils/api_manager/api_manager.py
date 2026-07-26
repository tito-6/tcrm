# Part of TCRM AI. See LICENSE for details.

"""
Single entry point for AI calls. Picks provider/key, calls adapter, retries on
rate limit/quota/error with next key or next provider.
"""

import logging
import time

from .key_pool import KeyPool
from .unified_types import AllProvidersExhaustedError
from .adapters import get_adapter

_logger = logging.getLogger(__name__)

MAX_RETRIES = 10


class TCRMApiManager:
    """Orchestrates key selection, adapter calls, and retry/fallover."""

    def __init__(self, env):
        self.env = env
        self.key_pool = KeyPool(env)

    def get_adapter(self, provider_code):
        adapter = get_adapter(provider_code)
        if not adapter:
            raise ValueError(f'Unknown provider: {provider_code}')
        return adapter

    def get_response(
        self,
        messages,
        tools=None,
        max_tokens=1000,
        temperature=0.7,
        timeout=45,
    ):
        tried_keys = set()
        attempts = 0

        while attempts < MAX_RETRIES:
            attempts += 1
            try:
                key_slot = self.key_pool.get_next_key()
            except AllProvidersExhaustedError as e:
                raise e

            if key_slot.id in tried_keys:
                break
            tried_keys.add(key_slot.id)

            adapter = self.get_adapter(key_slot.provider_code)
            # For Ollama, use system parameter tcrm.ai_base_url so the remote RAG proxy can be wired without storing URL in keys
            api_key = key_slot.api_key
            if key_slot.provider_code == 'ollama':
                ai_base_url = self.env['ir.config_parameter'].sudo().get_param('tcrm.ai_base_url', '').strip()
                if ai_base_url:
                    api_key = ai_base_url.rstrip('/')
            request = adapter.build_request(
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
                api_key=api_key,
                model=key_slot.default_model,
            )
            request['timeout'] = timeout

            start = time.time()
            try:
                raw = adapter.call(request)
            except Exception as e:
                err_msg = str(e)
                _logger.warning(
                    "TCRM AI adapter call failed for key %s: %s",
                    key_slot.key_label,
                    err_msg,
                )
                self.key_pool.report_error(key_slot, err_msg)
                continue

            latency_ms = int((time.time() - start) * 1000)

            if adapter.is_rate_limited(raw):
                if adapter.is_quota_exhausted(raw):
                    self.key_pool.report_exhausted(key_slot)
                else:
                    self.key_pool.report_rate_limited(key_slot)
                continue

            if adapter.is_quota_exhausted(raw):
                self.key_pool.report_exhausted(key_slot)
                continue

            if adapter.is_server_error(raw):
                try:
                    err_body = raw.text or str(raw.status_code)
                except Exception:
                    err_body = str(raw.status_code)
                self.key_pool.report_error(key_slot, err_body)
                continue

            if adapter.is_success(raw):
                unified = adapter.parse_response(raw)
                unified.key_label = key_slot.key_label
                unified.latency_ms = latency_ms
                self.key_pool.report_success(key_slot, unified.usage.total_tokens)
                return unified

            self.key_pool.report_error(key_slot, 'unknown_response')
            continue

        next_available = self.key_pool.get_next_available_time()
        raise AllProvidersExhaustedError(next_available)
