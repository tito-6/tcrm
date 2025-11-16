#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check if submitted_on field shows in tree view"""

import xmlrpc.client

ODOO_URL = 'http://localhost:8069'
DB_NAME = 'crm'
USERNAME = 'admin'
PASSWORD = 'admin'

def check_view():
    """Check tree view fields"""
    print("🔍 Checking tree view configuration...\n")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        
        if not uid:
            print("❌ Authentication failed")
            return
        
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        # Find our custom view
        view_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
            'ir.ui.view', 'search',
            [[['name', '=', 'crm.lead.tree.meta.inherit']]])
        
        if view_ids:
            print(f"✅ Found custom tree view: ID {view_ids[0]}")
            
            view_data = models.execute_kw(DB_NAME, uid, PASSWORD,
                'ir.ui.view', 'read',
                [view_ids, ['name', 'model', 'active', 'arch_db', 'priority']])
            
            print(f"   Model: {view_data[0]['model']}")
            print(f"   Active: {view_data[0]['active']}")
            print(f"   Priority: {view_data[0].get('priority', 16)}")
            
            # Check if submitted_on is in the arch
            arch = view_data[0]['arch_db']
            if 'submitted_on' in arch:
                print("   ✅ 'submitted_on' field IS in the view definition")
                if 'optional="show"' in arch or "optional='show'" in arch:
                    print("   ✅ Field has optional='show' attribute")
            else:
                print("   ❌ 'submitted_on' field NOT in view definition")
        else:
            print("❌ Custom tree view not found")
        
        # Check the base view
        base_view_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
            'ir.ui.view', 'search',
            [[['model', '=', 'crm.lead'], ['type', '=', 'tree']]])
        
        print(f"\n📊 Found {len(base_view_ids)} tree views for crm.lead model")
        
        # Get fields_view to see what the user actually sees
        print("\n🎯 Getting actual fields_view_get result...")
        fields_view = models.execute_kw(DB_NAME, uid, PASSWORD,
            'crm.lead', 'fields_view_get',
            [], {'view_type': 'tree'})
        
        arch = fields_view.get('arch', '')
        if 'submitted_on' in arch:
            print("✅ 'submitted_on' IS in the final rendered tree view!")
            print("\n📝 View excerpt showing submitted_on:")
            # Find and print the line
            for line in arch.split('\n'):
                if 'submitted_on' in line:
                    print(f"   {line.strip()}")
        else:
            print("❌ 'submitted_on' NOT in final rendered view")
            print("\n⚠️  This might mean:")
            print("   1. View inheritance didn't work")
            print("   2. Another view is overriding it")
            print("   3. Browser cache needs clearing")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    check_view()
