# Part of TCRM AI. See LICENSE for details.

"""Google Gemini — REST API. See https://ai.google.dev/gemini-api/docs/models."""

import requests

from .base_adapter import BaseAdapter
from ..unified_types import TokenUsage, UnifiedResponse

# Deprecated model IDs (no longer in v1beta) → current replacement
_GEMINI_MODEL_ALIASES = {
    'gemini-1.5-flash-8b': 'gemini-2.0-flash',
    'gemini-1.5-flash': 'gemini-2.0-flash',
    'gemini-1.5-pro': 'gemini-2.0-flash',
    'gemini-1.0-pro': 'gemini-2.0-flash',
    'gemini-pro': 'gemini-2.0-flash',
}

GEMINI_BASE = 'https://generativelanguage.googleapis.com/v1beta/models'


class GeminiAdapter(BaseAdapter):
    """Adapter for Google Gemini generateContent REST API."""

    def build_request(
        self,
        messages,
        tools=None,
        max_tokens=1000,
        temperature=0.7,
        api_key=None,
        model=None,
    ):
        contents = []
        system_instruction = None
        for msg in messages or []:
            role = (msg.get('role') or 'user').lower()
            content = msg.get('content') or ''
            if role == 'system':
                system_instruction = content
                continue
            if role == 'assistant':
                role = 'model'
            parts = [{'text': content}]
            contents.append({'role': role, 'parts': parts})
        body = {
            'contents': contents,
            'generationConfig': {
                'maxOutputTokens': max_tokens,
                'temperature': temperature,
            },
        }
        if system_instruction:
            body['systemInstruction'] = {'parts': [{'text': system_instruction}]}
        if tools:
            body['tools'] = [{'functionDeclarations': self._convert_tools(tools)}]
        model_id = _GEMINI_MODEL_ALIASES.get(model, model) or 'gemini-2.0-flash'
        url = f'{GEMINI_BASE}/{model_id}:generateContent?key={api_key}'
        return {'url': url, 'headers': {'Content-Type': 'application/json'}, 'json': body}

    def _convert_tools(self, tools):
        out = []
        for t in tools or []:
            if isinstance(t, dict) and t.get('type') == 'function':
                f = t.get('function', t)
                out.append({
                    'name': f.get('name', ''),
                    'description': f.get('description', ''),
                    'parameters': f.get('parameters', {'type': 'object', 'properties': {}}),
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
        usage = TokenUsage(0, 0, 0)
        candidates = (data.get('candidates') or [])
        if candidates:
            content = candidates[0].get('content', {})
            parts = content.get('parts', [])
            for p in parts:
                if 'text' in p:
                    text += p.get('text', '')
            usage_meta = data.get('usageMetadata', {})
            usage = TokenUsage(
                usage_meta.get('promptTokenCount', 0),
                usage_meta.get('totalTokenCount', 0) - usage_meta.get('promptTokenCount', 0),
                usage_meta.get('totalTokenCount', 0),
            )
        return UnifiedResponse(
            text=text,
            tool_calls=[],
            usage=usage,
            provider='gemini',
            model=data.get('modelVersion', ''),
            key_label='',
            latency_ms=0,
        )

    def is_rate_limited(self, raw_response):
        if raw_response.status_code == 429:
            return True
        try:
            body = raw_response.json()
            err = body.get('error', {}) or {}
            msg = (err.get('message') or '').lower()
            return 'resource_exhausted' in msg or 'quota' in msg or 'rate' in msg
        except Exception:
            return False

    def is_quota_exhausted(self, raw_response):
        if raw_response.status_code != 429:
            return False
        try:
            body = raw_response.json()
            msg = (body.get('error', {}).get('message') or '').lower()
            return ('quota' in msg and ('daily' in msg or 'monthly' in msg)) or 'dailylimitexceeded' in msg
        except Exception:
            return False

    def is_server_error(self, raw_response):
        return raw_response.status_code in (500, 502, 503, 504)

    def is_success(self, raw_response):
        return raw_response.status_code == 200 and raw_response.content
