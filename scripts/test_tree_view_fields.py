#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test what fields are actually available in the tree view"""

import xmlrpc.client
import json

ODOO_URL = 'http://localhost:8069'
DB_NAME = 'crm'
USERNAME = 'admin'
PASSWORD = 'admin'

def test_tree_view():
    """Get the actual tree view that Odoo renders"""
    print("🔍 Testing tree view fields availability...\n")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        
        if not uid:
            print("❌ Authentication failed")
            return
        
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        # Get the view using get_views (the correct Odoo 17 method)
        print("📊 Fetching tree view definition...\n")
        views = models.execute_kw(DB_NAME, uid, PASSWORD,
            'crm.lead', 'get_views',
            [[[False, 'list']]], {'options': {}})
        
        tree_view = views.get('views', {}).get('list', {})
        arch = tree_view.get('arch', '')
        
        print("="*80)
        print("TREE VIEW ARCHITECTURE")
        print("="*80)
        print(arch)
        print("\n")
        
        # Check if submitted_on is present
        if 'submitted_on' in arch:
            print("✅ 'submitted_on' IS PRESENT in the tree view!")
            print("\nExtracting the exact line:")
            for line in arch.split('\n'):
                if 'submitted_on' in line:
                    print(f"   {line.strip()}")
        else:
            print("❌ 'submitted_on' NOT FOUND in tree view")
            print("\n⚠️  Available fields in the view:")
            import re
            fields = re.findall(r'<field name="([^"]+)"', arch)
            for field in fields:
                print(f"   - {field}")
        
        # Also check field definitions
        print("\n" + "="*80)
        print("FIELD METADATA")
        print("="*80)
        
        fields_info = models.execute_kw(DB_NAME, uid, PASSWORD,
            'crm.lead', 'fields_get', 
            [['submitted_on', 'date_deadline', 'create_date']],
            {'attributes': ['string', 'type', 'store', 'readonly']})
        
        for field_name, field_info in fields_info.items():
            print(f"\n{field_name}:")
            print(f"   Label: {field_info.get('string')}")
            print(f"   Type: {field_info.get('type')}")
            print(f"   Stored: {field_info.get('store')}")
            print(f"   Readonly: {field_info.get('readonly')}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_tree_view()
