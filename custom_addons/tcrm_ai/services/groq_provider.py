# Part of TCRM AI. See LICENSE for details.
"""Reusable OpenAI-compatible Groq request service."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Generator, Iterable

import requests

from .constants import (
    APPROVED_GROQ_MODELS,
    DEFAULT_GROQ_MODEL,
    GROQ_BASE_URL,
    SAFE_ERROR_CODES,
    format_retry_after,
    rate_limit_user_message,
)
from .crypto import normalize_api_key

_logger = logging.getLogger(__name__)

APPROVED_MODEL_IDS = {m[0] for m in APPROVED_GROQ_MODELS}


class GroqProviderError(Exception):
    def __init__(
        self,
        code: str,
        message: str | None = None,
        diagnostics: str | None = None,
        retry_after: int | None = None,
        http_status: int | None = None,
    ):
        self.code = code
        self.retry_after = retry_after
        self.http_status = http_status
        if message:
            self.safe_message = message
        elif code in ('quota_exceeded', 'rate_limited'):
            self.safe_message = rate_limit_user_message(retry_after)
        else:
            self.safe_message = SAFE_ERROR_CODES.get(code, SAFE_ERROR_CODES['unknown'])
        self.diagnostics = diagnostics or ''
        super().__init__(self.safe_message)


def validate_model(model: str | None) -> str:
    model = (model or DEFAULT_GROQ_MODEL).strip()
    if model not in APPROVED_MODEL_IDS:
        raise GroqProviderError('model_denied')
    return model


def _parse_retry_after(resp) -> int | None:
    """Parse Retry-After / Groq rate-limit headers into seconds."""
    headers = getattr(resp, 'headers', None) or {}
    # Prefer explicit Retry-After (seconds or HTTP-date — we only handle seconds).
    raw = headers.get('Retry-After') or headers.get('retry-after')
    if raw is not None:
        try:
            return max(1, int(float(str(raw).strip())))
        except (TypeError, ValueError):
            pass
    for key in (
        'x-ratelimit-reset-requests',
        'x-ratelimit-reset-tokens',
        'x-ratelimit-reset',
        'retry-after-ms',
    ):
        val = headers.get(key) or headers.get(key.title())
        if val is None:
            continue
        text = str(val).strip().lower()
        try:
            if text.endswith('ms'):
                return max(1, int(float(text[:-2]) / 1000.0))
            if text.endswith('s'):
                return max(1, int(float(text[:-1])))
            if text.endswith('m'):
                return max(1, int(float(text[:-1]) * 60))
            # Unix timestamp vs relative seconds
            num = float(text)
            if num > 1_000_000_000:  # epoch
                return max(1, int(num - time.time()))
            return max(1, int(num))
        except (TypeError, ValueError):
            continue
    return None


def _map_http_error(status: int, body: dict | None, resp=None) -> GroqProviderError:
    err = (body or {}).get('error') or {}
    code = (err.get('code') or err.get('type') or '').lower()
    msg = (err.get('message') or '').lower()
    retry_after = _parse_retry_after(resp) if resp is not None else None
    diag = json.dumps({
        'status': status,
        'error_code': err.get('code'),
        'error_type': err.get('type'),
        'retry_after': retry_after,
    })
    if status == 408 or 'timeout' in code or 'timed out' in msg:
        return GroqProviderError('timeout', diagnostics=diag, http_status=status)
    if 'model_permission' in code or 'model_not_found' in code:
        return GroqProviderError('model_denied', diagnostics=diag, http_status=status)
    if status == 404 or ('model' in msg and ('does not exist' in msg or 'not found' in msg or 'permission' in msg)):
        return GroqProviderError('model_denied', diagnostics=diag, http_status=status)
    if status == 401 or 'invalid_api_key' in code or 'incorrect api key' in msg:
        return GroqProviderError('invalid_api_key', diagnostics=diag, http_status=status)
    if status == 403 and ('permission' in code or 'permission' in msg) and 'model' in (code + msg):
        return GroqProviderError('model_denied', diagnostics=diag, http_status=status)
    if status == 403:
        if 'model' in (code + msg) or 'permission' in (code + msg):
            return GroqProviderError('model_denied', diagnostics=diag, http_status=status)
        return GroqProviderError('forbidden', diagnostics=diag, http_status=status)
    if status == 429 or 'rate_limit' in code or 'quota' in msg:
        # Prefer rate_limited; keep quota_exceeded alias for older callers.
        return GroqProviderError(
            'rate_limited',
            message=rate_limit_user_message(retry_after or 18),
            diagnostics=diag,
            retry_after=retry_after or 18,
            http_status=status,
        )
    if status == 400:
        return GroqProviderError('invalid_configuration', diagnostics=diag, http_status=status)
    if status >= 500:
        return GroqProviderError('provider_unavailable', diagnostics=diag, http_status=status)
    return GroqProviderError('unknown', diagnostics=diag, http_status=status)


class GroqProviderService:
    """Backend-only Groq client. Never logs Authorization or API keys."""

    def __init__(
        self,
        api_key: str,
        base_url: str = GROQ_BASE_URL,
        model: str = DEFAULT_GROQ_MODEL,
        timeout: int = 45,
        max_retries: int = 1,
        correlation_id: str | None = None,
    ):
        key = normalize_api_key(api_key)
        if not key:
            raise GroqProviderError('invalid_api_key')
        self.api_key = key
        self.base_url = (base_url or GROQ_BASE_URL).rstrip('/')
        self.model = validate_model(model)
        self.timeout = max(5, min(120, int(timeout or 45)))
        self.max_retries = max(0, min(3, int(max_retries or 0)))
        self.correlation_id = (correlation_id or '')[:64]

    def _headers(self) -> dict:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % self.api_key,
        }
        if self.correlation_id:
            headers['X-Request-Id'] = self.correlation_id
        return headers

    def chat_completions(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        max_tokens: int = 512,
        temperature: float = 0.3,
        stream: bool = False,
        response_format: dict | None = None,
        tool_choice: str | None = None,
        allow_auto_retry: bool = True,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            'model': self.model,
            'messages': messages or [],
            'max_tokens': max(1, min(8192, int(max_tokens or 512))),
            'temperature': max(0.0, min(1.0, float(temperature))),
            'stream': bool(stream),
        }
        if tools:
            body['tools'] = tools
            if tool_choice:
                body['tool_choice'] = tool_choice
        if response_format:
            body['response_format'] = response_format

        url = '%s/chat/completions' % self.base_url
        attempt = 0
        last_exc: Exception | None = None
        auto_retried_429 = False

        while attempt <= self.max_retries:
            started = time.monotonic()
            try:
                resp = requests.post(
                    url,
                    headers=self._headers(),
                    json=body,
                    timeout=self.timeout,
                    stream=stream,
                )
            except requests.Timeout as exc:
                last_exc = exc
                _logger.warning(
                    'Groq timeout cid=%s attempt=%s', self.correlation_id or '-', attempt,
                )
                if attempt >= self.max_retries:
                    raise GroqProviderError('timeout') from exc
                attempt += 1
                time.sleep(0.4 * attempt)
                continue
            except requests.RequestException as exc:
                last_exc = exc
                _logger.warning(
                    'Groq unreachable cid=%s attempt=%s err=%s',
                    self.correlation_id or '-', attempt, type(exc).__name__,
                )
                if attempt >= self.max_retries:
                    raise GroqProviderError('provider_unavailable') from exc
                attempt += 1
                time.sleep(0.4 * attempt)
                continue

            latency_ms = int((time.monotonic() - started) * 1000)
            if stream:
                return {
                    'stream': resp,
                    'latency_ms': latency_ms,
                    'provider': 'groq',
                    'model': self.model,
                    'correlation_id': self.correlation_id,
                }

            try:
                data = resp.json() if resp.content else {}
            except ValueError:
                data = {}

            if resp.status_code == 200:
                usage = data.get('usage') or {}
                choice = (data.get('choices') or [{}])[0]
                message = choice.get('message') or {}
                return {
                    'text': message.get('content') or '',
                    'tool_calls': message.get('tool_calls') or [],
                    'finish_reason': choice.get('finish_reason'),
                    'usage': {
                        'prompt_tokens': int(usage.get('prompt_tokens') or 0),
                        'completion_tokens': int(usage.get('completion_tokens') or 0),
                        'total_tokens': int(usage.get('total_tokens') or 0),
                    },
                    'latency_ms': latency_ms,
                    'provider': 'groq',
                    'model': data.get('model') or self.model,
                    'raw_status': 200,
                    'correlation_id': self.correlation_id,
                }

            mapped = _map_http_error(resp.status_code, data, resp)
            # One bounded auto-retry for short 429 waits only.
            if (
                allow_auto_retry
                and not auto_retried_429
                and resp.status_code == 429
                and mapped.retry_after is not None
                and mapped.retry_after <= 5
            ):
                auto_retried_429 = True
                _logger.info(
                    'Groq 429 short retry cid=%s wait=%ss',
                    self.correlation_id or '-', mapped.retry_after,
                )
                time.sleep(mapped.retry_after)
                continue

            # Do not retry auth / permission / quota beyond the short path above.
            if resp.status_code in (400, 401, 403, 404, 408, 429):
                raise mapped
            if resp.status_code >= 500 and attempt < self.max_retries:
                attempt += 1
                time.sleep(0.4 * attempt)
                continue
            raise mapped

        raise GroqProviderError('provider_unavailable') from last_exc

    def test_connection(self) -> dict[str, Any]:
        """Minimal connection test; never returns headers or secrets."""
        result = self.chat_completions(
            messages=[
                {'role': 'system', 'content': 'Reply with OK only.'},
                {'role': 'user', 'content': 'ping'},
            ],
            max_tokens=8,
            temperature=0,
            allow_auto_retry=False,
        )
        return {
            'ok': True,
            'message': 'Groq bağlantısı başarılı.',
            'provider': 'groq',
            'model': result.get('model') or self.model,
            'latency_ms': result.get('latency_ms') or 0,
            'usage': result.get('usage') or {},
            'correlation_id': self.correlation_id,
        }

    def iter_sse_text(self, stream_response) -> Generator[str, None, None]:
        """Yield text deltas from an OpenAI-compatible SSE stream."""
        try:
            for line in stream_response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith('data: '):
                    payload = line[6:].strip()
                else:
                    continue
                if payload == '[DONE]':
                    break
                try:
                    data = json.loads(payload)
                except ValueError:
                    continue
                choices = data.get('choices') or []
                if not choices:
                    continue
                delta = (choices[0].get('delta') or {}).get('content') or ''
                if delta:
                    yield delta
        finally:
            try:
                stream_response.close()
            except Exception:
                pass


def trim_messages(messages: Iterable[dict], max_messages: int = 20) -> list[dict]:
    """Keep system + last N messages to bound context size."""
    msgs = list(messages or [])
    if not msgs:
        return []
    system = [m for m in msgs if m.get('role') == 'system'][:1]
    rest = [m for m in msgs if m.get('role') != 'system']
    if len(rest) > max_messages:
        rest = rest[-max_messages:]
    return system + rest
