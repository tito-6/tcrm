# Part of TCRM AI. See LICENSE for details.

import json
from unittest.mock import MagicMock, patch

from tcrm.tests import tagged, TransactionCase

from ..services.constants import format_retry_after, rate_limit_user_message
from ..services.groq_provider import GroqProviderError, GroqProviderService
from ..services.tools import TcrmAiToolExecutor, ToolDenied
from ..services import tools as tools_mod
from ..services import web_research


@tagged('tcrm_ai', 'post_install', '-at_install')
class TestTcrmAiEngineBehavior(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env['ir.config_parameter'].sudo().set_param('tcrm_ai.entitlement_state', 'active')
        self.config = self.env['tcrm.ai.config'].get_config()
        self.config.write({
            'ai_enabled': True,
            'api_key_input': 'gsk_test_key_abcdefghijklmnopqrstuv',
            'allow_crm_data': True,
            'allow_internet_research': True,
            'allow_payment_data': True,
            'save_conversation_history': True,
        })
        self.config.sudo().write({'last_connection_status': 'ok'})

    def test_greeting_fast_path_turkish(self):
        result = self.env['tcrm.ai.engine']._ask('merhaba')
        self.assertFalse(result.get('error'))
        self.assertEqual(result.get('status'), 'success')
        self.assertIn('Merhaba', result.get('answer') or '')
        self.assertNotIn('yardımcı olamam', (result.get('answer') or '').lower())
        self.assertTrue(result.get('correlation_id'))

    def test_no_generic_refusal_for_harmless(self):
        result = self.env['tcrm.ai.engine']._ask('selam')
        self.assertFalse(result.get('error'))
        self.assertNotRegex(result.get('answer') or '', r'yardımcı olamam')

    def test_crm_question_invokes_orm_tool(self):
        self.env['crm.lead'].create({'name': 'Engine Test Lead'})
        fake_tool_round = {
            'text': '',
            'tool_calls': [{
                'id': 'call_1',
                'type': 'function',
                'function': {'name': 'get_lead_summary', 'arguments': '{"days": 30}'},
            }],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15},
            'model': 'openai/gpt-oss-20b',
        }
        fake_final = {
            'text': 'Bu ay erişilebilir lead sayısı araç sonucuna göre hesaplandı.',
            'tool_calls': [],
            'usage': {'prompt_tokens': 20, 'completion_tokens': 10, 'total_tokens': 30},
            'model': 'openai/gpt-oss-20b',
        }
        with patch.object(GroqProviderService, 'chat_completions', side_effect=[fake_tool_round, fake_final]):
            result = self.env['tcrm.ai.engine']._ask('Bu ay kaç lead geldi?')
        self.assertFalse(result.get('error'))
        self.assertIn('get_lead_summary', result.get('tools_used') or [])

    def test_public_weather_invokes_web_tool(self):
        weather = {
            'ok': True,
            'city': 'Istanbul',
            'summary': 'Istanbul: 18°C, hissedilen 17°C, nem %60, Clear. Rüzgar 10 km/s.',
            'url': 'https://wttr.in/Istanbul',
            'citations': [{'title': 'Hava durumu — Istanbul', 'url': 'https://wttr.in/Istanbul'}],
            'retrieved_at': '2026-07-28T00:00:00Z',
        }
        with patch.object(tools_mod.web_research, 'get_weather', return_value=weather):
            executor = TcrmAiToolExecutor(self.env, self.config)
            data = json.loads(executor.execute('get_weather', {'city': 'Istanbul'}))
        self.assertEqual(data.get('source_type'), 'internet')
        self.assertTrue(data.get('citations'))
        self.assertIn('18°C', data.get('summary') or '')

    def test_unauthorized_other_tenant_rejected(self):
        executor = TcrmAiToolExecutor(self.env, self.config)
        with self.assertRaises(ToolDenied):
            executor.execute('search_business_records', {'db_name': 'other_tenant'})

    def test_secret_model_denied(self):
        executor = TcrmAiToolExecutor(self.env, self.config)
        with self.assertRaises(ToolDenied):
            executor.execute('search_business_records', {'model': 'ir.config_parameter'})

    def test_chat_status_hides_provider_key(self):
        status = self.env['tcrm.ai.config'].get_chat_status()
        self.assertNotIn('api_key_masked', status)
        self.assertNotIn('provider', status)
        self.assertNotIn('model', status)
        self.assertNotIn('usage', status)
        self.assertEqual(status.get('title'), 'TCRM AI Asistan')

    def test_engine_error_is_structured(self):
        with patch.object(GroqProviderService, 'chat_completions', side_effect=GroqProviderError(
            'rate_limited', retry_after=18, http_status=429,
        )):
            result = self.env['tcrm.ai.engine']._ask('pipeline özeti')
        self.assertTrue(result.get('error'))
        self.assertEqual(result.get('status'), 'rate_limited')
        self.assertEqual(result.get('retry_after'), 18)
        self.assertIn('saniye', result.get('answer') or '')
        self.assertNotIn('All AI services', result.get('answer') or '')


@tagged('tcrm_ai', 'post_install', '-at_install')
class TestGroqRateLimitHandling(TransactionCase):

    def test_retry_after_under_60_seconds(self):
        msg = format_retry_after(18)
        self.assertIn('18', msg)
        self.assertIn('saniye', msg)
        self.assertNotIn('0 dakika', msg)

    def test_retry_after_minutes(self):
        msg = format_retry_after(120)
        self.assertIn('2', msg)
        self.assertIn('dakika', msg)

    def test_rate_limit_user_message_no_zero_minutes(self):
        msg = rate_limit_user_message(0)
        self.assertNotIn('0 dakika', msg)
        self.assertIn('saniye', msg)

    def test_http_429_maps_rate_limited(self):
        svc = GroqProviderService(
            api_key='gsk_test_key_abcdefghijklmnopqrstuv',
            timeout=5,
            max_retries=0,
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {'Retry-After': '18'}
        mock_resp.content = b'{"error":{"code":"rate_limit_exceeded","message":"Rate limit"}}'
        mock_resp.json.return_value = {
            'error': {'code': 'rate_limit_exceeded', 'message': 'Rate limit'},
        }
        with patch('requests.post', return_value=mock_resp):
            with self.assertRaises(GroqProviderError) as ctx:
                svc.chat_completions([{'role': 'user', 'content': 'hi'}], max_tokens=8, allow_auto_retry=False)
        self.assertEqual(ctx.exception.code, 'rate_limited')
        self.assertEqual(ctx.exception.retry_after, 18)
        self.assertIn('saniye', ctx.exception.safe_message)
        self.assertNotIn('All AI services', ctx.exception.safe_message)

    def test_no_uncontrolled_retries_on_429(self):
        svc = GroqProviderService(
            api_key='gsk_test_key_abcdefghijklmnopqrstuv',
            timeout=5,
            max_retries=2,
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {'Retry-After': '30'}
        mock_resp.content = b'{"error":{"code":"rate_limit_exceeded"}}'
        mock_resp.json.return_value = {'error': {'code': 'rate_limit_exceeded'}}
        with patch('requests.post', return_value=mock_resp) as mocked:
            with self.assertRaises(GroqProviderError):
                svc.chat_completions([{'role': 'user', 'content': 'hi'}], max_tokens=8)
        self.assertEqual(mocked.call_count, 1)

    def test_ssrf_blocks_private_urls(self):
        with self.assertRaises(ValueError):
            web_research.validate_public_url('http://127.0.0.1/secret')
        with self.assertRaises(ValueError):
            web_research.validate_public_url('http://169.254.169.254/latest/meta-data')
        with self.assertRaises(ValueError):
            web_research.validate_public_url('file:///etc/passwd')
