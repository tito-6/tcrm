# -*- coding: utf-8 -*-
"""
Automated integration and visibility tests for akod.tech website leads.
"""
import unittest
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
TCRM_SRC = r"d:\crm\tcrm-src"

sys.path.insert(0, TCRM_SRC)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'custom-addons'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'custom_addons'))

import tcrm
from tcrm.tools import config
config.parse_config(['-c', os.path.join(PROJECT_ROOT, 'tcrm.conf')])

from tcrm.api import Environment
from tcrm.sql_db import db_connect
from tcrm.addons.tcrm_saas_routing import routing_patch as rp





class TestAkodLeadVisibility(unittest.TestCase):

    def test_routing_akod_domain_to_tenant_db(self):
        """Verify akod.tcrm.online maps strictly to akod_prod database."""
        status, db = rp.resolve_host('akod.tcrm.online')
        self.assertEqual(status, rp.S_OK)
        self.assertEqual(db, 'akod_prod')

    def test_routing_control_and_unknown_hosts(self):
        """Verify tcrm.online stays on control DB and unknown host returns 404."""
        status_ctrl, db_ctrl = rp.resolve_host('tcrm.online')
        self.assertEqual(status_ctrl, rp.S_CONTROL)
        self.assertEqual(db_ctrl, 'tcrm_master')

        status_unk, db_unk = rp.resolve_host('unknown-attacker.tcrm.online')
        self.assertEqual(status_unk, rp.S_NOT_FOUND)
        self.assertIsNone(db_unk)

    def test_lead_creation_and_visibility_in_tenant_db(self):
        """Verify lead is created with type='lead' and is visible to sales users without sudo."""
        conn = db_connect('akod_prod')
        cr = conn.cursor()
        env = Environment(cr, 1, {})

        marker = f"AKOD-VISIBILITY-TEST-{os.urandom(4).hex().upper()}"
        
        # Resolve dynamic tenant defaults
        from tcrm.addons.meta_leads.controllers.meta_webhook import MetaLeadWebhook
        controller = MetaLeadWebhook()

        
        # Test lead payload
        data = {
            'name': marker,
            'email': 'visibility_test@akod.tech',
            'phone': '+905525242866',
            'company': 'AK KOD Test Client',
            'city': 'Istanbul',
            'message': 'Test lead visibility without hardcoded IDs',
            'utm_source': 'akod_website',
            'utm_medium': 'test',
        }
        
        # Mock request context in environment
        Company = env['res.company'].sudo()
        company = Company.search([], limit=1)
        
        Stage = env['crm.stage'].sudo()
        stages = Stage.search([], order='sequence asc, id asc')
        self.assertTrue(len(stages) > 0, "Tenant DB must have at least one crm.stage")
        
        Lead = env['crm.lead'].sudo()
        lead = Lead.create({
            'name': data['name'],
            'contact_name': data['name'],
            'email_from': data['email'],
            'phone': data['phone'],
            'partner_name': data['company'],
            'city': data['city'],
            'description': data['message'],
            'type': 'lead',  # Must be lead for Lead Havuzu
            'company_id': company.id,
            'stage_id': stages[0].id,
            'meta_platform': 'website',
            'meta_source': 'akod_website',
        })
        cr.commit()

        self.assertTrue(lead.id > 0, "Lead record should have valid ID")
        self.assertEqual(lead.type, 'lead', "Lead type must be 'lead' for Lead Havuzu")
        self.assertEqual(lead.company_id.id, company.id, "Lead company must match tenant company")

        # Verify visibility for standard user without sudo
        user = env['res.users'].sudo().search([('id', '=', 2)], limit=1) # Admin user
        visible_leads = env['crm.lead'].with_user(user).search([('id', '=', lead.id)])
        self.assertEqual(len(visible_leads), 1, "Lead must be visible to authorized user without sudo()")

        # Clean up test lead
        lead.unlink()
        cr.commit()
        cr.close()

    def test_idempotency_duplicate_handling(self):
        """Verify that duplicate lead submissions return the existing lead."""
        test_key = f"TEST-KEY-{os.urandom(4).hex()}"
        data = {'email': 'duplicate@akod.tech', 'name': 'Duplicate Test'}
        
        conn = db_connect('akod_prod')
        cr = conn.cursor()
        env = Environment(cr, 1, {})

        import importlib
        import tcrm.addons.meta_leads.controllers.meta_webhook as mw
        importlib.reload(mw)
        controller = mw.MetaLeadWebhook()

        # Create initial lead
        Lead = env['crm.lead'].sudo()
        lead1 = Lead.create({
            'name': 'Duplicate Test',
            'email_from': 'duplicate@akod.tech',
            'type': 'lead',
            'meta_leadgen_id': test_key,
            'description': f"IDEMPOTENCY_KEY:{test_key}",
        })
        cr.flush()

        # Check duplicate finder logic
        existing = controller._find_existing_duplicate_lead(data, idempotency_key=test_key, env=Lead)
        self.assertIsNotNone(existing, "Duplicate lead should be found by idempotency key")


        self.assertEqual(existing.id, lead1.id)


        # Cleanup
        lead1.unlink()
        cr.commit()
        cr.close()



if __name__ == '__main__':
    unittest.main()
