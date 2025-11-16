#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Delete all leads from CRM"""

import xmlrpc.client

ODOO_URL = 'http://localhost:8069'
DB_NAME = 'crm'
USERNAME = 'admin'
PASSWORD = 'admin'

def delete_all_leads():
    """Delete all leads"""
    print("🗑️  Deleting all leads from CRM...\n")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        
        if not uid:
            print("❌ Authentication failed")
            return
        
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        # Get all leads
        lead_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
            'crm.lead', 'search', [[]])
        
        print(f"Found {len(lead_ids)} leads")
        
        if lead_ids:
            # Delete all leads
            models.execute_kw(DB_NAME, uid, PASSWORD,
                'crm.lead', 'unlink', [lead_ids])
            print(f"✅ Deleted {len(lead_ids)} leads\n")
        else:
            print("No leads to delete\n")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    delete_all_leads()
