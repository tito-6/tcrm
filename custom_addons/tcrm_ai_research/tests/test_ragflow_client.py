# Part of TCRM AI Research. See LICENSE for details.

from unittest.mock import MagicMock, patch

from tcrm.tests import TransactionCase, tagged

from ..services.exceptions import (
    RagflowAuthError,
    RagflowTimeoutError,
    RagflowValidationError,
)
from ..services.ragflow_client import RagflowResearchProvider


@tagged('tcrm_ai_research', 'post_install', '-at_install')
class TestRagflowClient(TransactionCase):

    def _provider(self, session):
        return RagflowResearchProvider(
            base_url='https://ragflow.example.com',
            api_key='test-key',
            timeout=5,
            max_retries=2,
            session=session,
            correlation_id='test-corr',
        )

    def test_auth_failure(self):
        session = MagicMock()
        response = MagicMock()
        response.status_code = 401
        session.request.return_value = response
        provider = self._provider(session)
        with self.assertRaises(RagflowAuthError):
            provider.list_datasets()

    def test_timeout_handling(self):
        import requests
        session = MagicMock()
        session.request.side_effect = requests.Timeout()
        provider = self._provider(session)
        with self.assertRaises(RagflowTimeoutError):
            provider.list_datasets()

    def test_malformed_upstream_response(self):
        session = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.json.side_effect = ValueError('bad json')
        session.request.return_value = response
        provider = self._provider(session)
        with self.assertRaises(RagflowValidationError):
            provider.list_datasets()

    def test_ask_normalizes_citations(self):
        session = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            'code': 0,
            'data': {
                'answer': 'Yanıt',
                'id': 'm1',
                'session_id': 's1',
                'reference': {
                    'chunks': [{
                        'document_name': 'doc.pdf',
                        'content': 'alıntı',
                        'similarity': 0.8,
                        'id': 'c1',
                        'document_id': 'd1',
                        'page_number': 3,
                    }],
                },
            },
        }
        session.request.return_value = response
        provider = self._provider(session)
        result = provider.ask('soru?', chat_id='chat-1', stream=False)
        self.assertEqual(result['answer'], 'Yanıt')
        self.assertEqual(result['citations'][0]['title'], 'doc.pdf')
        self.assertEqual(result['citations'][0]['page_number'], 3)

    def test_api_key_not_logged(self):
        session = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {'code': 0, 'data': []}
        session.request.return_value = response
        provider = self._provider(session)
        from ..services import ragflow_client as rf_mod
        with patch.object(rf_mod._logger, 'info') as logger:
            provider.list_datasets()
            for call in logger.call_args_list:
                self.assertNotIn('test-key', str(call))
                self.assertNotIn('Bearer', str(call))
