# Part of TCRM SaaS Core. See LICENSE for details.

from unittest.mock import MagicMock, patch

from tcrm.tests import tagged, TransactionCase


@tagged('tcrm_saas_core', 'post_install', '-at_install')
class TestTenantAppInventory(TransactionCase):

    def setUp(self):
        super().setUp()
        Company = self.env['res.company']
        self.company = Company.create({'name': 'Inventory Co'})
        self.tenant = self.env['tcrm.tenant'].sudo().create({
            'name': 'invtenant',
            'client_name': 'Inventory Tenant',
            'company_id': self.company.id,
            'db_name': False,
            'state': 'active',
        })

    def test_entitlement_vs_installation_states(self):
        Inventory = self.env['tcrm.tenant.app.inventory'].sudo()
        self.assertEqual(Inventory._compute_access_state('allowed', 'installed'), 'granted_installed')
        self.assertEqual(Inventory._compute_access_state('allowed', 'uninstalled'), 'granted_not_installed')
        self.assertEqual(Inventory._compute_access_state('blocked', 'installed'), 'installed_not_granted')
        self.assertEqual(Inventory._compute_access_state('allowed', 'unreachable'), 'unreachable')

    def test_sync_without_db_marks_unreachable(self):
        crm = self.env['ir.module.module'].sudo().search([('name', '=', 'crm')], limit=1)
        if crm:
            self.tenant.action_grant_module(crm, state='allowed')
        res = self.env['tcrm.tenant.app.inventory'].action_sync_tenant(self.tenant)
        self.assertFalse(res.get('ok'))
        self.assertEqual(res.get('error'), 'no_db')

    def test_revoke_does_not_uninstall(self):
        Inventory = self.env['tcrm.tenant.app.inventory'].sudo()
        row = Inventory.create({
            'tenant_id': self.tenant.id,
            'technical_name': 'crm',
            'name': 'CRM',
            'installed_state': 'installed',
            'entitlement_state': 'allowed',
            'access_state': 'granted_installed',
            'is_application': True,
        })
        crm = self.env['ir.module.module'].sudo().search([('name', '=', 'crm')], limit=1)
        if crm:
            self.tenant.action_grant_module(crm, state='allowed')
        row.action_revoke_access()
        self.assertEqual(row.entitlement_state, 'blocked')
        self.assertEqual(row.installed_state, 'installed')
        self.assertEqual(row.access_state, 'installed_not_granted')

    def test_protected_modules_cannot_uninstall(self):
        Inventory = self.env['tcrm.tenant.app.inventory'].sudo()
        self.assertFalse(Inventory._can_uninstall('base'))
        self.assertFalse(Inventory._can_uninstall('mail'))
        self.assertFalse(Inventory._can_uninstall('web'))
        self.assertTrue(Inventory._can_uninstall('website'))
        self.assertTrue(Inventory._can_uninstall('crm'))

    def test_sync_reads_tenant_modules_when_reachable(self):
        self.tenant.db_name = 'fake_inventory_db'
        Inventory = self.env['tcrm.tenant.app.inventory'].sudo()

        fake_mod = MagicMock()
        fake_mod.name = 'crm'
        fake_mod.shortdesc = 'CRM'
        fake_mod.latest_version = '1.0'
        fake_mod.installed_version = '1.0'
        fake_mod.application = True
        fake_mod.state = 'installed'
        fake_mod.category_id = MagicMock(display_name='Sales')

        fake_module_model = MagicMock()
        fake_module_model.search.return_value = [fake_mod]
        fake_env = {'ir.module.module': fake_module_model}

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        class FakeRegistry:
            def cursor(self):
                return FakeCursor()

        fake_api = MagicMock()
        fake_api.Environment.return_value = fake_env

        with patch.object(Inventory, '_open_tenant_env', return_value=(FakeRegistry(), fake_api, 1)):
            res = Inventory.action_sync_tenant(self.tenant)

        self.assertTrue(res.get('ok'))
        row = Inventory.search([
            ('tenant_id', '=', self.tenant.id),
            ('technical_name', '=', 'crm'),
        ], limit=1)
        self.assertTrue(row)
        self.assertEqual(row.installed_state, 'installed')
        self.assertEqual(row.name, 'CRM')

    def test_technical_filter_default(self):
        Inventory = self.env['tcrm.tenant.app.inventory'].sudo()
        Inventory.create({
            'tenant_id': self.tenant.id,
            'technical_name': 'base',
            'name': 'Base',
            'is_application': False,
            'is_technical': True,
            'installed_state': 'installed',
            'entitlement_state': 'none',
            'access_state': 'installed_not_granted',
        })
        Inventory.create({
            'tenant_id': self.tenant.id,
            'technical_name': 'crm',
            'name': 'CRM',
            'is_application': True,
            'is_technical': False,
            'installed_state': 'installed',
            'entitlement_state': 'allowed',
            'access_state': 'granted_installed',
        })
        user_facing = Inventory.search([
            ('tenant_id', '=', self.tenant.id),
            ('is_technical', '=', False),
        ])
        self.assertEqual(len(user_facing), 1)
        self.assertEqual(user_facing.technical_name, 'crm')

    def test_stale_indicator(self):
        Inventory = self.env['tcrm.tenant.app.inventory'].sudo()
        row = Inventory.create({
            'tenant_id': self.tenant.id,
            'technical_name': 'sale_management',
            'name': 'Sales',
            'installed_state': 'installed',
            'entitlement_state': 'allowed',
            'access_state': 'granted_installed',
            'last_sync': False,
            'last_sync_result': 'ok',
        })
        self.assertTrue(row.stale)
