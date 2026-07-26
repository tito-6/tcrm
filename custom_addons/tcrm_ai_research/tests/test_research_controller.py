# Part of TCRM AI Research. See LICENSE for details.

from tcrm.tests import tagged

from .common import AiResearchCommon


@tagged('tcrm_ai_research', 'post_install', '-at_install')
class TestResearchController(AiResearchCommon):

    def test_controller_validation_requires_question(self):
        conv = self.env['tcrm.ai.conversation'].with_user(self.user_ai).create({
            'workspace_id': self.workspace.id,
            'lead_id': self.lead.id,
        })
        # Direct model validation path used by controller
        from tcrm.exceptions import UserError
        with self.assertRaises(UserError):
            conv.ask_question('   ')

    def test_public_config_via_service(self):
        from ..services.config import public_config_dict
        cfg = public_config_dict(self.env)
        self.assertIn('allowed_extensions', cfg)
        self.assertNotIn('api_key', cfg)

    def test_auth_failure_sets_message_error(self):
        self.fake.fail_auth = True
        conv = self.env['tcrm.ai.conversation'].with_user(self.user_ai).create({
            'workspace_id': self.workspace.id,
            'lead_id': self.lead.id,
        })
        result = conv.ask_question('Merhaba')
        msg = self.env['tcrm.ai.message'].browse(result['assistant_message_id'])
        self.assertEqual(msg.status, 'error')

    def test_timeout_sets_message_error(self):
        self.fake.fail_timeout = True
        conv = self.env['tcrm.ai.conversation'].with_user(self.user_ai).create({
            'workspace_id': self.workspace.id,
        })
        result = conv.ask_question('timeout please')
        msg = self.env['tcrm.ai.message'].browse(result['assistant_message_id'])
        self.assertEqual(msg.status, 'error')
