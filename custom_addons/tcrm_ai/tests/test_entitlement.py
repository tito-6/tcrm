# Part of TCRM AI. See LICENSE for details.

from unittest.mock import patch

from tcrm.tests import tagged, TransactionCase

from ..services import entitlement as entitlement_svc
from ..services.constants import ENTITLEMENT_PARAM


@tagged('tcrm_ai', 'post_install', '-at_install')
class TestTcrmAiEntitlement(TransactionCase):

    def setUp(self):
        super().setUp()
        self.config = self.env['tcrm.ai.config'].get_config()
        self.ICP = self.env['ir.config_parameter'].sudo()

    def test_module_disabled_without_entitlement(self):
        self.ICP.set_param(ENTITLEMENT_PARAM, 'unavailable')
        self.config.write({'ai_enabled': True, 'api_key_input': 'gsk_abcdefghijklmnopqrstuvwxyz1234'})
        result = self.env['tcrm.ai.engine']._ask('Bu ay kaç yeni lead geldi?')
        self.assertTrue(result.get('error'))
        self.assertIn('etkin değil', result.get('answer', '').lower() + result.get('answer', ''))

    def test_entitlement_revocation_blocks_requests(self):
        self.ICP.set_param(ENTITLEMENT_PARAM, 'active')
        self.config.write({'ai_enabled': True, 'api_key_input': 'gsk_abcdefghijklmnopqrstuvwxyz1234'})
        entitlement_svc.set_entitlement_state(self.env, 'unavailable')
        result = self.env['tcrm.ai.engine']._ask('test')
        self.assertTrue(result.get('error') or result.get('disabled'))

    def test_config_required_state(self):
        entitlement_svc.set_entitlement_state(self.env, 'config_required')
        self.config.write({'ai_enabled': False, 'api_key_encrypted': False})
        reason = entitlement_svc.chat_block_reason(self.env)
        self.assertTrue(reason)

    def test_no_secret_copied_during_provision_seed(self):
        """Empty disabled config must not inherit any owner key."""
        self.config.clear_api_key()
        self.assertFalse(self.config.has_api_key)
        self.assertFalse(self.config._get_plaintext_api_key())

    def test_master_local_configuration_independent(self):
        """Master DB config is local to current database name."""
        self.config.write({'api_key_input': 'gsk_master_local_key_value_0001'})
        self.assertEqual(self.env.cr.dbname, self.env['tcrm.ai.usage'].sudo().create({
            'company_id': self.env.company.id,
            'user_id': self.env.user.id,
        }).database_name)

    def test_suspend_blocks(self):
        entitlement_svc.set_entitlement_state(self.env, 'suspended')
        ok, code = entitlement_svc.entitlement_allows_requests(self.env)
        self.assertFalse(ok)
        self.assertEqual(code, 'suspended')
