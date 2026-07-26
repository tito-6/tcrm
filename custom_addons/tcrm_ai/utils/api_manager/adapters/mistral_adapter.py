# Part of TCRM AI. See LICENSE for details.

"""Mistral AI — REST API."""

import json

import requests

from .base_adapter import BaseAdapter
from ..unified_types import TokenUsage, UnifiedResponse


MISTRAL_BASE = 'https://api.mistral.ai/v1'


class MistralAdapter(BaseAdapter):
    """Adapter for Mistral chat/completions REST API."""

    def build_request(
        self,
        messages,
        tools=None,
        max_tokens=1000,
        temperature=0.7,
        api_key=None,
        model=None,
    ):
        body = {
            'model': model,
            'messages': messages or [],
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        if tools:
            body['tools'] = tools
        return {
            'url': f'{MISTRAL_BASE}/chat/completions',
            'headers': {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
            },
            'json': body,
        }

    def call(self, request):
        return requests.post(
            request['url'],
            headers=request['headers'],
            json=request['json'],
            timeout=request.get('timeout', 45),
        )

    def parse_response(self, raw_response):
        data = raw_response.json()
        choice = (data.get('choices') or [{}])[0]
        msg = choice.get('message', {})
        text = msg.get('content') or ''
        usage_data = data.get('usage', {})
        usage = TokenUsage(
            usage_data.get('prompt_tokens', 0),
            usage_data.get('completion_tokens', 0),
            usage_data.get('total_tokens', 0),
        )
        tool_calls = []
        for tc in msg.get('tool_calls') or []:
            fn = tc.get('function', {})
            try:
                args = json.loads(fn.get('arguments') or '{}')
            except Exception:
                args = {}
            tool_calls.append({'name': fn.get('name', ''), 'arguments': args})
        return UnifiedResponse(
            text=text,
            tool_calls=tool_calls,
            usage=usage,
            provider='mistral',
            model=data.get('model', ''),
            key_label='',
            latency_ms=0,
        )

    def is_rate_limited(self, raw_response):
        return raw_response.status_code == 429

    def is_quota_exhausted(self, raw_response):
        return raw_response.status_code == 402

    def is_server_error(self, raw_response):
        return raw_response.status_code in (500, 502, 503, 504)

    def is_success(self, raw_response):
        return raw_response.status_code == 200 and raw_response.content
