# Part of TCRM AI. See LICENSE for details.

"""Ollama — local or remote Ollama API (e.g. VPS RAG proxy)."""

import requests

from .base_adapter import BaseAdapter
from ..unified_types import TokenUsage, UnifiedResponse


def _base_url(api_key):
    """Use api_key as base URL for Ollama (e.g. http://45.9.191.119:8000)."""
    if api_key and isinstance(api_key, str) and api_key.strip().lower().startswith('http'):
        return api_key.strip().rstrip('/')
    return 'http://localhost:11434'


class OllamaAdapter(BaseAdapter):
    """Adapter for Ollama chat API. Base URL is taken from api_key (e.g. VPS proxy)."""

    def build_request(
        self,
        messages,
        tools=None,
        max_tokens=1000,
        temperature=0.7,
        api_key=None,
        model=None,
    ):
        base = _base_url(api_key)
        body = {
            'model': model or 'qwen2.5:3b',
            'messages': messages or [],
            'stream': False,
            'options': {
                'num_predict': max_tokens,
                'temperature': temperature,
            },
        }
        return {
            'url': f'{base}/api/chat',
            'headers': {'Content-Type': 'application/json'},
            'json': body,
        }

    def call(self, request):
        return requests.post(
            request['url'],
            headers=request['headers'],
            json=request['json'],
            timeout=request.get('timeout', 60),
        )

    def parse_response(self, raw_response):
        data = raw_response.json()
        msg = data.get('message') or {}
        text = msg.get('content') or ''
        prompt_count = data.get('prompt_eval_count') or 0
        eval_count = data.get('eval_count') or 0
        usage = TokenUsage(
            input_tokens=prompt_count,
            output_tokens=eval_count,
            total_tokens=prompt_count + eval_count,
        )
        return UnifiedResponse(
            text=text,
            tool_calls=[],
            usage=usage,
            provider='ollama',
            model=data.get('model', ''),
            key_label='',
            latency_ms=0,
        )

    def is_rate_limited(self, raw_response):
        return raw_response.status_code == 429

    def is_quota_exhausted(self, raw_response):
        return False

    def is_server_error(self, raw_response):
        return raw_response.status_code in (500, 502, 503, 504)

    def is_success(self, raw_response):
        return raw_response.status_code == 200 and raw_response.content
