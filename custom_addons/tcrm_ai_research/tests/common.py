# Part of TCRM AI Research. See LICENSE for details.
"""Shared test helpers and injectable fake RAGFlow provider."""

from tcrm.tests import TransactionCase, tagged

from ..services.base_provider import BaseResearchProvider


class FakeResearchProvider(BaseResearchProvider):
    """In-memory fake used by tests (no live RAGFlow)."""

    def __init__(self):
        self.sessions = {}
        self.documents = {}
        self.asks = []
        self.deleted = []
        self.fail_auth = False
        self.fail_timeout = False
        self.malformed = False
        self.upload_count = 0

    def create_dataset(self, name, **kwargs):
        return {'id': 'ds-1', 'name': name}

    def list_datasets(self, name=None, **kwargs):
        return [{'id': 'ds-1', 'name': name or 'default'}]

    def create_chat(self, name, dataset_ids, **kwargs):
        return {'id': 'chat-1', 'name': name, 'dataset_ids': dataset_ids}

    def create_session(self, chat_id, name='New session', **kwargs):
        if self.fail_auth:
            from ..services.exceptions import RagflowAuthError
            raise RagflowAuthError()
        sid = f'sess-{len(self.sessions) + 1}'
        self.sessions[sid] = {'chat_id': chat_id, 'name': name}
        return {'id': sid, 'name': name}

    def upload_document(self, dataset_id, filename, content, content_type=None, **kwargs):
        self.upload_count += 1
        doc_id = f'doc-{self.upload_count}'
        self.documents[doc_id] = {
            'id': doc_id,
            'dataset_id': dataset_id,
            'name': filename,
            'run': 'UNSTART',
            'size': len(content),
        }
        return self.documents[doc_id]

    def parse_documents(self, dataset_id, document_ids, **kwargs):
        for doc_id in document_ids:
            if doc_id in self.documents:
                self.documents[doc_id]['run'] = 'DONE'
        return {'ok': True}

    def get_document_status(self, dataset_id, document_id, **kwargs):
        doc = self.documents.get(document_id)
        if not doc:
            from ..services.exceptions import RagflowNotFoundError
            raise RagflowNotFoundError()
        return {
            'id': document_id,
            'name': doc['name'],
            'run': doc.get('run', 'DONE'),
            'progress': 1.0,
            'raw': {},
        }

    def delete_document(self, dataset_id, document_ids, **kwargs):
        for doc_id in document_ids:
            self.deleted.append(doc_id)
            self.documents.pop(doc_id, None)
        return {'ok': True}

    def ask(self, question, *, chat_id=None, session_id=None, stream=False, **kwargs):
        if self.fail_auth:
            from ..services.exceptions import RagflowAuthError
            raise RagflowAuthError()
        if self.fail_timeout:
            from ..services.exceptions import RagflowTimeoutError
            raise RagflowTimeoutError()
        if self.malformed:
            from ..services.exceptions import RagflowValidationError
            raise RagflowValidationError('Malformed upstream response')
        self.asks.append({'question': question, 'chat_id': chat_id, 'session_id': session_id})
        return {
            'answer': f'Answer for: {question[:80]}',
            'session_id': session_id or 'sess-auto',
            'message_id': 'msg-1',
            'citations': [{
                'title': 'Kaynak Belge',
                'page_number': 2,
                'chunk_text': 'Türkçe örnek alıntı — ğüşıöç',
                'source_url': '',
                'score': 0.91,
                'external_reference': 'chunk-1',
                'document_external_id': '',
            }],
            'partial': False,
            'raw_reference': {},
        }


@tagged('tcrm_ai_research')
class AiResearchCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fake = FakeResearchProvider()
        # Patch factory used by models/services
        from ..services import ragflow_client
        cls._orig_factory = ragflow_client.get_research_provider
        ragflow_client.get_research_provider = lambda env, correlation_id=None: cls.fake

        cls.company = cls.env.company
        cls.user_ai = cls.env['res.users'].create({
            'name': 'AI Research User',
            'login': 'ai_research_user',
            'email': 'ai_user@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('tcrm_ai_research.group_ai_research_user').id,
                cls.env.ref('sales_team.group_sale_salesman').id,
            ])],
            'company_ids': [(6, 0, [cls.company.id])],
            'company_id': cls.company.id,
        })
        cls.user_other = cls.env['res.users'].create({
            'name': 'Other User',
            'login': 'ai_research_other',
            'email': 'other@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('tcrm_ai_research.group_ai_research_user').id,
            ])],
            'company_ids': [(6, 0, [cls.company.id])],
            'company_id': cls.company.id,
        })
        cls.manager = cls.env['res.users'].create({
            'name': 'AI Manager',
            'login': 'ai_research_manager',
            'email': 'manager@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('tcrm_ai_research.group_ai_research_manager').id,
                cls.env.ref('sales_team.group_sale_salesman').id,
            ])],
            'company_ids': [(6, 0, [cls.company.id])],
            'company_id': cls.company.id,
        })
        cls.workspace = cls.env['tcrm.ai.workspace'].with_user(cls.manager).create({
            'name': 'Test Workspace',
            'company_id': cls.company.id,
            'owner_id': cls.manager.id,
            'member_ids': [(6, 0, [cls.manager.id, cls.user_ai.id])],
            'ragflow_dataset_id': 'ds-1',
            'ragflow_assistant_id': 'chat-1',
            'default_language': 'tr',
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Müşteri Örnek'})
        cls.lead = cls.env['crm.lead'].with_user(cls.user_ai).create({
            'name': 'Fırsat Örnek',
            'partner_id': cls.partner.id,
            'type': 'opportunity',
        })

    @classmethod
    def tearDownClass(cls):
        from ..services import ragflow_client
        ragflow_client.get_research_provider = cls._orig_factory
        super().tearDownClass()
