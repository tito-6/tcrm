# Part of TCRM AI Research. See LICENSE for details.

from tcrm.tests import tagged

from .common import AiResearchCommon


@tagged('tcrm_ai_research', 'post_install', '-at_install')
class TestSaveNote(AiResearchCommon):

    def test_save_result_as_crm_note(self):
        conv = self.env['tcrm.ai.conversation'].with_user(self.user_ai).create({
            'workspace_id': self.workspace.id,
            'lead_id': self.lead.id,
            'partner_id': self.partner.id,
            'res_model': 'crm.lead',
            'res_id': self.lead.id,
            'language': 'tr',
        })
        result = conv.ask_question('Özetle')
        msg = self.env['tcrm.ai.message'].with_user(self.user_ai).browse(result['assistant_message_id'])
        before = len(self.lead.message_ids)
        msg.action_save_as_note()
        self.lead.invalidate_recordset()
        self.assertGreater(len(self.lead.message_ids), before)
        bodies = ' '.join(self.lead.message_ids.mapped('body'))
        self.assertIn('AI Research Result', bodies)

    def test_attach_result(self):
        conv = self.env['tcrm.ai.conversation'].with_user(self.user_ai).create({
            'workspace_id': self.workspace.id,
            'lead_id': self.lead.id,
            'res_model': 'crm.lead',
            'res_id': self.lead.id,
        })
        result = conv.ask_question('Attach me')
        msg = self.env['tcrm.ai.message'].with_user(self.user_ai).browse(result['assistant_message_id'])
        out = msg.action_attach_result()
        self.assertTrue(out.get('attachment_id'))
