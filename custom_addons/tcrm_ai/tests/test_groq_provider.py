# Part of TCRM AI. See LICENSE for details.

from unittest.mock import MagicMock, patch

from tcrm.tests import tagged, TransactionCase

from ..services.constants import DEFAULT_GROQ_MODEL
from ..services.groq_provider import GroqProviderError, GroqProviderService, validate_model


@tagged('tcrm_ai', 'post_install', '-at_install')
class TestGroqProvider(TransactionCase):

    def test_validate_model_ok(self):
        self.assertEqual(validate_model(DEFAULT_GROQ_MODEL), DEFAULT_GROQ_MODEL)

    def test_validate_model_rejects_arbitrary(self):
        with self.assertRaises(GroqProviderError):
            validate_model('not-an-approved-model')

    def test_connection_test_success_mocked(self):
        svc = GroqProviderService(api_key='gsk_test_key_abcdefghijklmnopqrstuv', model=DEFAULT_GROQ_MODEL, timeout=10, max_retries=0)
        fake = {
            'text': 'OK',
            'tool_calls': [],
            'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2},
            'latency_ms': 12,
            'provider': 'groq',
            'model': DEFAULT_GROQ_MODEL,
            'raw_status': 200,
        }
        with patch.object(GroqProviderService, 'chat_completions', return_value=fake):
            result = svc.test_connection()
        self.assertTrue(result['ok'])
        self.assertEqual(result['message'], 'Groq bağlantısı başarılı.')
        self.assertNotIn('Authorization', str(result))
        self.assertNotIn('gsk_', str(result))

    def test_invalid_key_handling(self):
        svc = GroqProviderService(api_key='gsk_invalid_key_xxxxxxxxxxxx', model=DEFAULT_GROQ_MODEL, timeout=5, max_retries=0)
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.content = b'{"error":{"code":"invalid_api_key","message":"Incorrect API key"}}'
        mock_resp.json.return_value = {'error': {'code': 'invalid_api_key', 'message': 'Incorrect API key'}}
        with patch('requests.post', return_value=mock_resp):
            with self.assertRaises(GroqProviderError) as ctx:
                svc.chat_completions([{'role': 'user', 'content': 'hi'}], max_tokens=8)
        self.assertEqual(ctx.exception.code, 'invalid_api_key')
        self.assertIn('geçersiz', ctx.exception.safe_message.lower())

    def test_config_action_test_connection_records_status(self):
        config = self.env['tcrm.ai.config'].get_config()
        config.write({
            'api_key_input': 'gsk_test_key_abcdefghijklmnopqrstuv',
            'ai_enabled': True,
        })
        self.env['ir.config_parameter'].sudo().set_param('tcrm_ai.entitlement_state', 'active')
        fake = {
            'ok': True,
            'message': 'Groq bağlantısı başarılı.',
            'provider': 'groq',
            'model': DEFAULT_GROQ_MODEL,
            'latency_ms': 15,
            'usage': {},
        }
        with patch.object(GroqProviderService, 'test_connection', return_value=fake):
            config.action_test_connection()
        self.assertEqual(config.last_connection_status, 'ok')
