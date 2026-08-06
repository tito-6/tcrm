# -*- coding: utf-8 -*-
"""Control-plane job tests: signed jobs, validation, no browser-supplied inputs.

These run against the control DB and do NOT provision a real database.
"""
from tcrm.tests.common import TransactionCase, tagged
from tcrm.exceptions import UserError


@tagged('post_install', '-at_install')
class TestProvisioningJobs(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Tenant = self.env['tcrm.tenant']
        self.Domain = self.env['tcrm.tenant.domain']
        self.Job = self.env['tcrm.provisioning.job']
        self.company = self.env['res.company'].create({'name': 'Prov Test Co'})
        self.tenant = self.Tenant.create({
            'name': 'Prov Test', 'company_id': self.company.id,
            'state': 'draft', 'active': True,
        })
        self.Domain.create({
            'tenant_id': self.tenant.id, 'domain': 'prov-test.tcrm.online',
            'is_primary': True, 'active': True, 'verified': True,
        })
        # Ensure a signing secret exists.
        if not self.env['ir.config_parameter'].sudo().get_param('database.secret'):
            self.env['ir.config_parameter'].sudo().set_param('database.secret', 'test-secret')

    def test_enqueue_creates_signed_job(self):
        self.tenant.db_name = 'prov_test_db'
        job = self.Job.enqueue_for_tenant(self.tenant, 'prov_test_db')
        self.assertEqual(job.state, 'queued')
        self.assertEqual(job.db_name, 'prov_test_db')
        self.assertTrue(job.token)
        self.assertTrue(job.verify_token(), 'job signature must verify')
        # Module set is resolved server-side, not empty, and valid.
        self.assertTrue(job.module_set)
        self.assertIn('tcrm_saas_core', job.module_set)

    def test_enqueue_rejects_bad_db_name(self):
        with self.assertRaises(ValueError):
            self.Job.enqueue_for_tenant(self.tenant, 'Bad-Name')

    def test_enqueue_rejects_duplicate_db_mapping(self):
        other_company = self.env['res.company'].create({'name': 'Other Co'})
        other = self.Tenant.create({'name': 'Other', 'company_id': other_company.id})
        other.db_name = 'shared_db'
        with self.assertRaises(UserError):
            self.Job.enqueue_for_tenant(self.tenant, 'shared_db')

    def test_no_concurrent_jobs(self):
        self.Job.enqueue_for_tenant(self.tenant, 'prov_test_db')
        with self.assertRaises(UserError):
            self.Job.enqueue_for_tenant(self.tenant, 'prov_test_db')

    def test_action_request_provisioning_requires_valid_db(self):
        # 'ab' passes the core no-space/no-hyphen constraint but fails our stricter
        # validator (min length 3), so the action itself must reject it.
        self.tenant.db_name = 'ab'
        with self.assertRaises(UserError):
            self.tenant.action_request_provisioning()

    def test_action_request_provisioning_requires_domain(self):
        c2 = self.env['res.company'].create({'name': 'No Domain Co'})
        t2 = self.Tenant.create({'name': 'No Domain', 'company_id': c2.id})
        t2.db_name = 'no_domain_db'
        with self.assertRaises(UserError):
            t2.action_request_provisioning()

    def test_action_request_provisioning_happy_path(self):
        self.tenant.db_name = 'prov_test_db'
        self.tenant.action_request_provisioning()
        self.assertEqual(self.tenant.provision_state, 'queued')
        job = self.tenant.provisioning_job_ids[:1]
        self.assertTrue(job)
        self.assertEqual(job.state, 'queued')

    def test_claim_next_marks_running_and_verifies_signature(self):
        job = self.Job.enqueue_for_tenant(self.tenant, 'prov_test_db')
        claimed = self.Job.claim_next(worker_host='utest')
        self.assertEqual(claimed.id, job.id)
        self.assertEqual(claimed.state, 'running')
        self.assertEqual(claimed.attempts, 1)

    def test_claim_next_fails_on_tampered_signature(self):
        job = self.Job.enqueue_for_tenant(self.tenant, 'prov_test_db')
        # Tamper: change db_name directly in the row (bypassing enqueue), then
        # invalidate the ORM cache so the worker reads the tampered value.
        self.env.cr.execute(
            "UPDATE tcrm_provisioning_job SET db_name='evil_db' WHERE id=%s", (job.id,))
        self.env.invalidate_all()
        claimed = self.Job.claim_next(worker_host='utest')
        # Signature no longer matches -> claim returns empty and job is failed.
        self.assertFalse(claimed)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'failed')

    def test_retry_requeues_failed_job_with_new_token(self):
        job = self.Job.enqueue_for_tenant(self.tenant, 'prov_test_db')
        old_token = job.token
        job.mark_failed('boom')
        job.action_retry()
        self.assertEqual(job.state, 'queued')
        self.assertNotEqual(job.token, old_token)
        self.assertTrue(job.verify_token())
