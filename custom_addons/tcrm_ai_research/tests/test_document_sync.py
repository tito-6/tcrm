# Part of TCRM AI Research. See LICENSE for details.

import base64

from tcrm.tests import tagged

from .common import AiResearchCommon


@tagged('tcrm_ai_research', 'post_install', '-at_install')
class TestDocumentSync(AiResearchCommon):

    def test_checksum_avoids_duplicate_upload(self):
        content = b'hello research'
        att = self.env['ir.attachment'].with_user(self.user_ai).create({
            'name': 'note.txt',
            'type': 'binary',
            'datas': base64.b64encode(content),
            'mimetype': 'text/plain',
            'res_model': 'crm.lead',
            'res_id': self.lead.id,
        })
        doc = self.env['tcrm.ai.document'].with_user(self.user_ai).create({
            'name': 'note.txt',
            'workspace_id': self.workspace.id,
            'attachment_id': att.id,
            'sync_state': 'pending',
        })
        doc.action_sync()
        self.assertEqual(doc.sync_state, 'processing')
        self.assertTrue(doc.ragflow_document_id)
        self.assertEqual(self.fake.upload_count, 1)
        doc.action_sync()
        self.assertEqual(self.fake.upload_count, 1)

    def test_status_ready_after_refresh(self):
        content = b'doc'
        att = self.env['ir.attachment'].with_user(self.user_ai).create({
            'name': 'a.txt',
            'type': 'binary',
            'datas': base64.b64encode(content),
            'res_model': 'crm.lead',
            'res_id': self.lead.id,
        })
        doc = self.env['tcrm.ai.document'].with_user(self.user_ai).create({
            'name': 'a.txt',
            'workspace_id': self.workspace.id,
            'attachment_id': att.id,
        })
        doc.action_sync()
        doc.action_refresh_status()
        self.assertEqual(doc.sync_state, 'ready')

    def test_turkish_unicode_question_and_citation(self):
        conv = self.env['tcrm.ai.conversation'].with_user(self.user_ai).create({
            'workspace_id': self.workspace.id,
            'lead_id': self.lead.id,
            'partner_id': self.partner.id,
            'language': 'tr',
        })
        result = conv.ask_question('Bu müşteri için özet çıkar — ğüşıöç')
        msg = self.env['tcrm.ai.message'].browse(result['assistant_message_id'])
        self.assertEqual(msg.status, 'done')
        self.assertTrue(msg.citation_ids)
        self.assertIn('ğüşıöç', msg.citation_ids[0].chunk_text)
