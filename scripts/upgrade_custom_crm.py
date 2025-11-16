#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upgrade custom_crm_integration module to add submitted_on field"""

import xmlrpc.client
import time

ODOO_URL = 'http://localhost:8069'
DB_NAME = 'crm'
USERNAME = 'admin'
PASSWORD = 'admin'

def upgrade_module():
    """Upgrade the custom_crm_integration module"""
    print("🔧 Upgrading custom_crm_integration module...\n")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        
        if not uid:
            print("❌ Authentication failed")
            return False
        
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        # Find the module
        module_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
            'ir.module.module', 'search',
            [[['name', '=', 'custom_crm_integration']]])
        
        if not module_ids:
            print("❌ Module custom_crm_integration not found")
            return False
        
        print(f"✅ Found module ID: {module_ids[0]}")
        
        # Upgrade the module
        print("📦 Upgrading module...")
        models.execute_kw(DB_NAME, uid, PASSWORD,
            'ir.module.module', 'button_immediate_upgrade',
            [module_ids])
        
        print("✅ Module upgraded successfully!\n")
        print("⏳ Waiting for upgrade to complete...")
        time.sleep(10)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == '__main__':
    if upgrade_module():
        print("\n✅ Upgrade complete! You can now import leads with the 'submitted_on' field.")
    else:
        print("\n❌ Upgrade failed!")
