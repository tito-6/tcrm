#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import xmlrpc.client

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(project_root)
sys.path.insert(0, parent_dir)

def main():
    """Upgrade the WhatsApp module to load security rules"""
    
    # Connection parameters
    url = 'http://localhost:8069'
    db = 'crm'
    username = 'admin'
    password = 'admin'
    
    try:
        print("Connecting to Odoo...")
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("❌ Authentication failed!")
            return
            
        print("✅ Connected to Odoo")
        
        # Get models proxy
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        print("\n🔍 Searching for WhatsApp Business Integration module:")
        
        # Find the module
        module = models.execute_kw(db, uid, password,
            'ir.module.module', 'search_read',
            [[['name', '=', 'whatsapp_business_integration']]],
            {'fields': ['id', 'name', 'state', 'latest_version'], 'limit': 1}
        )
        
        if not module:
            print("❌ Module not found!")
            return
            
        module_info = module[0]
        print(f"📦 Module found: ID={module_info['id']}, State={module_info['state']}")
        
        if module_info['state'] == 'installed':
            print("\n🔧 Upgrading module to reload security rules...")
            
            # Trigger module upgrade
            try:
                result = models.execute_kw(db, uid, password,
                    'ir.module.module', 'button_immediate_upgrade',
                    [module_info['id']]
                )
                print(f"✅ Module upgrade triggered: {result}")
                
                print("\n⏱️ Waiting for upgrade to complete...")
                import time
                time.sleep(5)  # Wait a bit for the upgrade
                
                # Check module state again
                updated_module = models.execute_kw(db, uid, password,
                    'ir.module.module', 'read',
                    [module_info['id']],
                    {'fields': ['state']}
                )
                
                print(f"📦 Module state after upgrade: {updated_module[0]['state']}")
                
            except Exception as e:
                print(f"❌ Upgrade failed: {str(e)}")
                
        print("\n🔒 Checking access rules after upgrade:")
        try:
            access_rules = models.execute_kw(db, uid, password,
                'ir.model.access', 'search_read',
                [[['model_id.model', 'like', 'whatsapp%']]],
                {'fields': ['id', 'name', 'model_id', 'group_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink']}
            )
            
            if access_rules:
                print(f"✅ Found {len(access_rules)} access rules:")
                for rule in access_rules:
                    group = rule['group_id'][1] if rule['group_id'] else "All Users"
                    model = rule['model_id'][1] if rule['model_id'] else "Unknown"
                    perms = f"R:{rule['perm_read']} W:{rule['perm_write']} C:{rule['perm_create']} U:{rule['perm_unlink']}"
                    print(f"  🔐 {rule['name']}: {model} - {group} - {perms}")
            else:
                print("❌ Still no access rules found!")
                
        except Exception as e:
            print(f"❌ Error checking access rules: {str(e)}")
    
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")

if __name__ == '__main__':
    main()