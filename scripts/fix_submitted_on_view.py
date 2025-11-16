#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clear all user view preferences and force submitted_on to be visible"""

import xmlrpc.client

ODOO_URL = 'http://localhost:8069'
DB_NAME = 'crm'
USERNAME = 'admin'
PASSWORD = 'admin'

def fix_view():
    """Clear user preferences and check view"""
    print("🔧 Fixing view preferences...\n")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        
        if not uid:
            print("❌ Authentication failed")
            return
        
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        # Step 1: Delete all user view customizations for crm.lead list view
        print("🗑️  Deleting user view customizations...")
        custom_view_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
            'ir.ui.view.custom', 'search',
            [[['user_id', '=', uid], ['ref_id.model', '=', 'crm.lead']]])
        
        if custom_view_ids:
            models.execute_kw(DB_NAME, uid, PASSWORD,
                'ir.ui.view.custom', 'unlink', [custom_view_ids])
            print(f"   ✅ Deleted {len(custom_view_ids)} custom views")
        else:
            print("   ℹ️  No custom views found")
        
        # Step 2: Check our view's priority
        print("\n🔍 Checking view inheritance...")
        view_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
            'ir.ui.view', 'search',
            [[['name', '=', 'crm.lead.tree.meta.inherit']]])
        
        if view_ids:
            view = models.execute_kw(DB_NAME, uid, PASSWORD,
                'ir.ui.view', 'read',
                [view_ids, ['name', 'active', 'priority', 'mode', 'arch_db']])
            
            print(f"   View ID: {view[0]['id']}")
            print(f"   Active: {view[0]['active']}")
            print(f"   Priority: {view[0]['priority']}")
            print(f"   Mode: {view[0]['mode']}")
            
            # Make sure it's active with high priority
            if not view[0]['active'] or view[0]['priority'] > 10:
                print("   🔧 Fixing view settings...")
                models.execute_kw(DB_NAME, uid, PASSWORD,
                    'ir.ui.view', 'write',
                    [view_ids, {'active': True, 'priority': 1}])
                print("   ✅ View updated")
        
        # Step 3: Get the final rendered view
        print("\n📊 Getting final rendered view...")
        views = models.execute_kw(DB_NAME, uid, PASSWORD,
            'crm.lead', 'get_views',
            [[[False, 'list']]], {'options': {}})
        
        tree_view = views.get('views', {}).get('list', {})
        arch = tree_view.get('arch', '')
        
        # Check field position
        if 'submitted_on' in arch:
            print("   ✅ 'submitted_on' is in the view!")
            
            # Extract the line
            for i, line in enumerate(arch.split('\n')):
                if 'submitted_on' in line:
                    print(f"\n   Line {i}: {line.strip()}")
                    
                    # Check what's before and after
                    lines = arch.split('\n')
                    if i > 0:
                        print(f"   Before: {lines[i-1].strip()}")
                    if i < len(lines) - 1:
                        print(f"   After: {lines[i+1].strip()}")
        else:
            print("   ❌ 'submitted_on' NOT in view!")
        
        # Step 4: Check if it's in the fields list
        print("\n🔍 Checking view fields metadata...")
        fields = tree_view.get('fields', {})
        
        if 'submitted_on' in fields:
            print(f"   ✅ 'submitted_on' in fields metadata:")
            print(f"      Type: {fields['submitted_on'].get('type')}")
            print(f"      String: {fields['submitted_on'].get('string')}")
            print(f"      Readonly: {fields['submitted_on'].get('readonly')}")
        else:
            print("   ❌ 'submitted_on' NOT in fields metadata")
            print(f"   Available fields: {list(fields.keys())[:10]}...")
        
        # Step 5: Try to fetch actual lead data
        print("\n📋 Testing data fetch...")
        leads = models.execute_kw(DB_NAME, uid, PASSWORD,
            'crm.lead', 'search_read',
            [[]], {'fields': ['name', 'create_date', 'submitted_on'], 'limit': 3})
        
        for lead in leads:
            print(f"   ID {lead['id']}: {lead['name'][:30]}")
            print(f"      Created: {lead.get('create_date', 'N/A')}")
            print(f"      Submitted: {lead.get('submitted_on', 'N/A')}")
        
        print("\n" + "="*80)
        print("✅ DIAGNOSTIC COMPLETE")
        print("="*80)
        print("\nNOW DO THIS:")
        print("1. Close your browser COMPLETELY (all tabs)")
        print("2. Reopen and go to: http://localhost:8069")
        print("3. Login again")
        print("4. Go to CRM > Leads")
        print("5. Click the OPTIONS icon (⚙️ or ≡) at top-right of the list")
        print("6. Look for 'Submitted On' in the dropdown")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_view()
