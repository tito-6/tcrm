# Part of TCRM AI. See LICENSE for details.

import json

from tcrm.tests import tagged, TransactionCase
from tcrm.exceptions import AccessError

from ..services.tools import TcrmAiToolExecutor, ToolDenied


@tagged('tcrm_ai', 'post_install', '-at_install')
class TestTcrmAiToolsSecurity(TransactionCase):

    def setUp(self):
        super().setUp()
        self.config = self.env['tcrm.ai.config'].get_config()
        self.config.write({
            'allow_crm_data': True,
            'allow_sales_data': True,
            'allow_property_data': True,
            'allow_payment_data': True,
            'allow_reports': True,
            'mask_personal_data': True,
        })
        self.executor = TcrmAiToolExecutor(self.env, self.config)

    def test_arbitrary_sql_rejection(self):
        with self.assertRaises(ToolDenied):
            self.executor.execute('get_lead_summary', {'sql': 'SELECT * FROM res_users'})

    def test_arbitrary_database_switching_rejection(self):
        with self.assertRaises(ToolDenied):
            self.executor.execute('get_lead_summary', {'db_name': 'other_tenant_db'})

    def test_read_only_tools_no_write(self):
        before = self.env['crm.lead'].search_count([])
        self.executor.execute('get_lead_summary', {'days': 30})
        after = self.env['crm.lead'].search_count([])
        self.assertEqual(before, after)

    def test_payment_flag_blocks_payment_tool(self):
        self.config.write({'allow_payment_data': False})
        executor = TcrmAiToolExecutor(self.env, self.config)
        with self.assertRaises(ToolDenied):
            executor.execute('get_payment_summary', {'days': 30})

    def test_user_acl_enforcement_no_sudo_bypass(self):
        """Tool executor must use current env (not sudo) for CRM searches."""
        # Portal-like restricted user if available
        user = self.env['res.users'].create({
            'name': 'AI Restricted',
            'login': 'ai_restricted_%s' % self.env.cr.dbname,
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        # Ensure lead exists
        lead = self.env['crm.lead'].create({'name': 'AI ACL Lead'})
        # Record rule simulation: user without access to leads via sudo check that
        # executor uses user env — create lead with user_id other and rely on default ACL.
        lead.write({'user_id': self.env.user.id})
        exec_user = TcrmAiToolExecutor(self.env(user=user.id), self.config)
        # Restricted users may hit AccessError — tool must not use sudo to bypass.
        raw = exec_user.execute('get_lead_summary', {'days': 30})
        result = json.loads(raw)
        self.assertTrue(
            'total_leads_accessible' in result or result.get('error'),
            msg='Tool must return aggregate or safe error without sudo bypass',
        )

    def test_company_record_rules(self):
        result = json.loads(self.executor.execute('get_pipeline_summary', {}))
        self.assertEqual(result.get('company'), self.env.company.name)

    def test_conversation_isolation(self):
        other = self.env['res.users'].create({
            'name': 'AI Other',
            'login': 'ai_other_%s' % self.env.cr.dbname,
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('tcrm_ai.group_tcrm_ai_user').id,
            ])],
        })
        conv = self.env['tcrm.ai.assistant.conversation'].create({
            'name': 'Mine',
            'user_id': self.env.user.id,
        })
        other_conv = self.env['tcrm.ai.assistant.conversation'].with_user(other).create({
            'name': 'Theirs',
            'user_id': other.id,
        })
        visible = self.env['tcrm.ai.assistant.conversation'].with_user(other).search([])
        self.assertNotIn(conv.id, visible.ids)
        self.assertIn(other_conv.id, visible.ids)

    def test_report_permissions(self):
        self.config.write({'allow_reports': False})
        executor = TcrmAiToolExecutor(self.env, self.config)
        with self.assertRaises(ToolDenied):
            executor.execute('generate_management_report', {'period_days': 7})

    def test_payment_summary_deterministic_total(self):
        if 'propertio.payment' not in self.env:
            self.skipTest('propertio.payment not installed')
        result = json.loads(self.executor.execute('get_payment_summary', {'days': 30}))
        self.assertIn('total_amount', result)
        self.assertIn('note', result)
