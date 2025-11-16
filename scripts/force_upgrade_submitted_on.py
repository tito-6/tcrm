#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Force upgrade module to add submitted_on field"""

import xmlrpc.client
import time

ODOO_URL = 'http://localhost:8069'
DB_NAME = 'crm'
USERNAME = 'admin'
PASSWORD = 'admin'

def upgrade_module():
    """Force upgrade custom_crm_integration module"""
    print("🔄 Force upgrading custom_crm_integration module...\n")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        
        if not uid:
            print("❌ Authentication failed")
            return False
        
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        # Search for the module
        module_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
            'ir.module.module', 'search',
            [[['name', '=', 'custom_crm_integration']]])
        
        if not module_ids:
            print("❌ Module 'custom_crm_integration' not found")
            return False
        
        print(f"✅ Found module ID: {module_ids[0]}")
        
        # Get current state
        module_info = models.execute_kw(DB_NAME, uid, PASSWORD,
            'ir.module.module', 'read',
            [module_ids, ['state', 'latest_version']])
        
        print(f"   Current state: {module_info[0]['state']}")
        print(f"   Version: {module_info[0]['latest_version']}")
        
        # Force upgrade by marking as 'to upgrade'
        print("\n🔧 Marking module for upgrade...")
        models.execute_kw(DB_NAME, uid, PASSWORD,
            'ir.module.module', 'button_immediate_upgrade',
            [module_ids])
        
        print("✅ Module upgrade triggered!")
        print("⏳ Waiting for upgrade to complete...")
        
        # Wait a bit for the upgrade
        time.sleep(5)
        
        # Check field existence
        print("\n🔍 Verifying submitted_on field...")
        fields_info = models.execute_kw(DB_NAME, uid, PASSWORD,
            'crm.lead', 'fields_get', [],
            {'attributes': ['string', 'type', 'store']})
        
        if 'submitted_on' in fields_info:
            print("✅ SUCCESS! Field 'submitted_on' is now in the database!")
            print(f"   String: {fields_info['submitted_on'].get('string')}")
            print(f"   Type: {fields_info['submitted_on'].get('type')}")
            return True
        else:
            print("❌ Field 'submitted_on' still not found")
            return False
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == '__main__':
    success = upgrade_module()
    if success:
        print("\n" + "="*80)
        print("✅ MODULE UPGRADED SUCCESSFULLY!")
        print("="*80)
        print("\n🎯 Next steps:")
        print("   1. Press Ctrl+F5 in your browser to clear cache")
        print("   2. Go to: http://localhost:8069/web#action=217&model=crm.lead&view_type=list")
        print("   3. Click on column options (top right)")
        print("   4. You should now see 'Submitted On' field!")
    else:
        print("\n❌ Upgrade failed. Check the errors above.")
