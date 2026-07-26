# Part of TCRM AI. See LICENSE for details.

"""Anthropic Claude — REST API."""

import json

import requests

from .base_adapter import BaseAdapter
from ..unified_types import TokenUsage, UnifiedResponse


ANTHROPIC_BASE = 'https://api.anthropic.com/v1'


class AnthropicAdapter(BaseAdapter):
    """Adapter for Anthropic Messages API."""

    def build_request(
        self,
        messages,
        tools=None,
        max_tokens=1000,
        temperature=0.7,
        api_key=None,
        model=None,
    ):
        system = ''
        msgs = []
        for m in messages or []:
            role = (m.get('role') or 'user').lower()
            content = m.get('content') or ''
            if role == 'system':
                system = content
                continue
            msgs.append({'role': role, 'content': content})
        body = {
            'model': model,
            'max_tokens': max_tokens,
            'messages': msgs,
        }
        if system:
            body['system'] = system
        if tools:
            body['tools'] = self._convert_tools(tools)
        return {
            'url': f'{ANTHROPIC_BASE}/messages',
            'headers': {
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
            },
            'json': body,
        }

    def _convert_tools(self, tools):
        out = []
        for t in tools or []:
            if isinstance(t, dict) and t.get('type') == 'function':
                f = t.get('function', t)
                out.append({
                    'name': f.get('name', ''),
                    'description': f.get('description', ''),
                    'input_schema': f.get('parameters', {'type': 'object', 'properties': {}}),
                })
        return out

    def call(self, request):
        return requests.post(
            request['url'],
            headers=request['headers'],
            json=request['json'],
            timeout=request.get('timeout', 45),
        )

    def parse_response(self, raw_response):
        data = raw_response.json()
        text = ''
        tool_calls = []
        for block in data.get('content', []):
            if block.get('type') == 'text':
                text += block.get('text', '')
            if block.get('type') == 'tool_use':
                tool_calls.append({
                    'name': block.get('name', ''),
                    'arguments': block.get('input', {}),
                })
        usage = data.get('usage', {})
        token_usage = TokenUsage(
            usage.get('input_tokens', 0),
            usage.get('output_tokens', 0),
            usage.get('input_tokens', 0) + usage.get('output_tokens', 0),
        )
        return UnifiedResponse(
            text=text,
            tool_calls=tool_calls,
            usage=token_usage,
            provider='anthropic',
            model=data.get('model', ''),
            key_label='',
            latency_ms=0,
        )

    def is_rate_limited(self, raw_response):
        if raw_response.status_code == 429:
            return True
        remaining = raw_response.headers.get('anthropic-ratelimit-requests-remaining', '1')
        try:
            return int(remaining) == 0
        except Exception:
            return False

    def is_quota_exhausted(self, raw_response):
        if raw_response.status_code == 529:
            return True
        if raw_response.status_code != 429:
            return False
        try:
            body = raw_response.json()
            err = body.get('error', {})
            return (err.get('type') == 'rate_limit_error' and
                    'monthly' in (err.get('message') or '').lower())
        except Exception:
            return False

    def is_server_error(self, raw_response):
        return raw_response.status_code in (500, 502, 503, 504)

    def is_success(self, raw_response):
        return raw_response.status_code == 200 and raw_response.content
