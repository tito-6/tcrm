# Part of TCRM AI. See LICENSE for details.

from tcrm.tests import tagged, TransactionCase

from ..services.rate_limit import RateLimitError, check_and_consume, usage_dashboard


@tagged('tcrm_ai', 'post_install', '-at_install')
class TestTcrmAiUsageLimits(TransactionCase):

    def setUp(self):
        super().setUp()
        self.config = self.env['tcrm.ai.config'].get_config()
        self.config.write({
            'daily_request_limit': 2,
            'daily_token_limit': 100000,
            'rpm_limit': 10,
            'monthly_usage_limit': 1000000,
        })

    def test_token_tracking_on_usage_row(self):
        row = self.env['tcrm.ai.usage'].sudo().start_request()
        row.finish(usage={'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}, duration_ms=42, tools=['get_lead_summary'], success=True, model='openai/gpt-oss-20b')
        self.assertEqual(row.total_tokens, 15)
        self.assertEqual(row.tool_count, 1)
        self.assertFalse(row.in_flight)
        self.assertGreater(row.estimated_cost, 0)

    def test_usage_limits_block(self):
        Usage = self.env['tcrm.ai.usage'].sudo()
        for _ in range(2):
            Usage.create({
                'company_id': self.env.company.id,
                'user_id': self.env.user.id,
                'success': True,
                'total_tokens': 1,
            })
        with self.assertRaises(RateLimitError):
            check_and_consume(self.env, self.config)

    def test_usage_dashboard(self):
        self.env['tcrm.ai.usage'].sudo().create({
            'company_id': self.env.company.id,
            'user_id': self.env.user.id,
            'success': True,
            'total_tokens': 11,
            'duration_ms': 100,
            'tools_used': 'get_lead_summary',
        })
        dash = usage_dashboard(self.env)
        self.assertGreaterEqual(dash['requests_today'], 1)
        self.assertGreaterEqual(dash['tokens_today'], 11)

    def test_public_status_never_includes_key(self):
        self.config.write({'api_key_input': 'gsk_status_check_key_value_7788'})
        status = self.env['tcrm.ai.config'].get_public_status()
        blob = str(status)
        self.assertNotIn('gsk_status_check_key_value_7788', blob)
        self.assertNotIn('api_key_encrypted', status)
        self.assertTrue(status.get('configured'))
