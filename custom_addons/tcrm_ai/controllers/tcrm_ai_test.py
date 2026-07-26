# Part of TCRM AI. See LICENSE for details.

import logging
import time

import requests as py_requests

from tcrm import http
from tcrm.http import request

_logger = logging.getLogger(__name__)


class TcrmAiTestController(http.Controller):

    @http.route('/tcrm_ai/test_ollama', type='jsonrpc', auth='user')
    def test_ollama(self, base_url=None):
        """
        Test Ollama connectivity:
        1. GET {base_url}/api/version → check reachable
        2. GET {base_url}/api/tags → list models
        Returns: {connected: bool, version: str, models: [str]}
        """
        url = (base_url or '').strip().rstrip('/')
        if not url:
            url = request.env['ir.config_parameter'].sudo().get_param(
                'tcrm_ai.ollama_url', 'http://localhost:11434'
            )
        result = {'connected': False, 'version': '', 'models': [], 'error': ''}
        try:
            # Check version
            resp = py_requests.get(f'{url}/api/version', timeout=5)
            if resp.status_code != 200:
                result['error'] = f'HTTP {resp.status_code} from {url}/api/version'
                return result
            result['connected'] = True
            result['version'] = resp.json().get('version', 'unknown')
            # List models
            resp = py_requests.get(f'{url}/api/tags', timeout=10)
            if resp.status_code == 200:
                models_list = resp.json().get('models', [])
                result['models'] = [
                    {
                        'name': m.get('name', '?'),
                        'size': m.get('size', 0),
                    }
                    for m in models_list
                ]
        except Exception as e:
            result['error'] = str(e)
        return result

    @http.route('/tcrm_ai/test_key', type='jsonrpc', auth='user')
    def test_key(self, key_id):
        """
        Test a specific API key by sending a minimal prompt.
        Returns: {success: bool, message: str, latency_ms: int}
        """
        result = {'success': False, 'message': '', 'latency_ms': 0}
        try:
            key = request.env['tcrm.ai.key'].sudo().browse(int(key_id))
            if not key.exists():
                result['message'] = 'Key not found'
                return result

            from tcrm_ai.utils.api_manager.adapters import get_adapter
            provider = key.provider_id
            adapter = get_adapter(provider.provider_code)
            if not adapter:
                result['message'] = f'No adapter for provider: {provider.provider_code}'
                return result

            model = key.model_override or provider.default_model
            start = time.time()
            req = adapter.build_request(
                messages=[{'role': 'user', 'content': 'Say: OK'}],
                api_key=key.api_key,
                model=model,
                max_tokens=5,
            )
            raw = adapter.call(req)
            latency = int((time.time() - start) * 1000)
            result['latency_ms'] = latency

            if adapter.is_success(raw):
                key.mark_success(0)
                result['success'] = True
                result['message'] = f'Working ({latency}ms)'
            elif adapter.is_rate_limited(raw) or adapter.is_quota_exhausted(raw):
                key.mark_rate_limited()
                result['message'] = 'Rate limited or quota exceeded'
            else:
                err = getattr(raw, 'text', None) or str(raw.status_code)
                key.mark_error(err[:200])
                result['message'] = err[:200]
        except Exception as e:
            result['message'] = str(e)[:200]
        return result
