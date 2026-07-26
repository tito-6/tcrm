# Part of TCRM AI. See LICENSE for details.

"""Groq — OpenAI-compatible REST API."""

import json

import requests

from .base_adapter import BaseAdapter
from ..unified_types import TokenUsage, UnifiedResponse


GROQ_BASE = 'https://api.groq.com/openai/v1'


class GroqAdapter(BaseAdapter):
    """Adapter for Groq OpenAI-compatible chat/completions."""

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
            'url': f'{GROQ_BASE}/chat/completions',
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
            provider='groq',
            model=data.get('model', ''),
            key_label='',
            latency_ms=0,
        )

    def is_rate_limited(self, raw_response):
        if raw_response.status_code == 429:
            return True
        rem = raw_response.headers.get('x-ratelimit-remaining-requests', '1')
        rem_tok = raw_response.headers.get('x-ratelimit-remaining-tokens', '1')
        try:
            return int(rem) == 0 or int(rem_tok) == 0
        except Exception:
            return False

    def is_quota_exhausted(self, raw_response):
        if raw_response.status_code != 429:
            return False
        try:
            body = raw_response.json()
            err = body.get('error', {})
            msg = (err.get('message') or '').lower()
            return ('rate_limit_exceeded' in (err.get('code') or '') or
                    'tokens per day' in msg or 'requests per day' in msg)
        except Exception:
            return False

    def is_server_error(self, raw_response):
        return raw_response.status_code in (500, 502, 503, 504)

    def is_success(self, raw_response):
        return raw_response.status_code == 200 and raw_response.content
