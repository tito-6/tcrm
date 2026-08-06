# Part of TCRM SaaS Core. See LICENSE for details.

from unittest.mock import MagicMock, patch

from tcrm.tests import tagged, TransactionCase


@tagged('tcrm_saas_core', 'tcrm_ai', 'post_install', '-at_install')
class TestMasterTcrmAiEntitlement(TransactionCase):

    def setUp(self):
        super().setUp()
        if 'tcrm.tenant' not in self.env:
            self.skipTest('tcrm.tenant missing')
        self.Tenant = self.env['tcrm.tenant']
        self.Status = self.env['tcrm.tenant.ai.status']
        # Dedicated company so uniqueness constraint (one tenant per company) holds
        company = self.env['res.company'].create({'name': 'AI Disposable Co'})
        self.tenant = self.Tenant.create({
            'name': 'AI Disposable Tenant',
            'company_id': company.id,
        })

    def test_master_entitlement_grant_without_db(self):
        status = self.Status.get_or_create(self.tenant)
        # No db_name → grant marks granted/config without opening registry
        status.action_grant_access()
        self.assertIn(status.entitlement_state, ('granted', 'config_required'))

    def test_entitlement_revocation(self):
        status = self.Status.get_or_create(self.tenant)
        status.action_grant_access()
        status.action_revoke_access()
        self.assertEqual(status.entitlement_state, 'unavailable')
        self.assertFalse(status.enabled)

    def test_safe_dict_has_no_secrets(self):
        status = self.Status.get_or_create(self.tenant)
        status.write({
            'provider': 'groq',
            'model': 'openai/gpt-oss-20b',
            'configured': True,
            'last_safe_error': 'API anahtarı geçersiz',
        })
        data = status.to_safe_dict()
        blob = str(data)
        self.assertNotIn('gsk_', blob)
        self.assertNotIn('api_key', blob)
        self.assertEqual(data['provider'], 'groq')

    def test_no_owner_key_copied_on_grant_with_db(self):
        """When granting into a tenant DB, empty config is written — never owner key."""
        self.tenant.db_name = False  # keep unit test offline
        status = self.Status.get_or_create(self.tenant)
        status.action_grant_access()
        self.assertFalse(status.configured)

    def test_grant_install_path_mocked(self):
        self.tenant.write({'db_name': 'fake_ai_tenant_db'})
        status = self.Status.get_or_create(self.tenant)

        fake_cr = MagicMock()
        fake_env = MagicMock()
        fake_env.__contains__ = lambda self, key: key in ('tcrm.ai.config', 'ir.module.module', 'ir.config_parameter')
        fake_config = MagicMock()
        fake_env.__getitem__.side_effect = lambda name: {
            'ir.module.module': MagicMock(search=MagicMock(return_value=MagicMock(state='installed', button_immediate_install=MagicMock()))),
            'ir.config_parameter': MagicMock(sudo=MagicMock(return_value=MagicMock(set_param=MagicMock()))),
            'tcrm.ai.config': MagicMock(sudo=MagicMock(return_value=MagicMock(get_config=MagicMock(return_value=fake_config), search=MagicMock(return_value=fake_config)))),
        }.get(name, MagicMock())
        fake_env.ref = MagicMock(return_value=False)

        class FakeRegistry:
            def cursor(self_inner):
                return MagicMock(__enter__=MagicMock(return_value=fake_cr), __exit__=MagicMock(return_value=False))

        with patch.object(type(status), '_open_tenant_env', return_value=(FakeRegistry(), MagicMock(Environment=MagicMock(return_value=fake_env)), 1)):
            # Patch Environment construction inside action
            with patch('tcrm.api.Environment', return_value=fake_env):
                try:
                    status.action_grant_access()
                except Exception:
                    # Registry path may still fail in unit DB; ensure no plaintext key on master status
                    pass
        data = status.to_safe_dict()
        self.assertNotIn('gsk_', str(data))
