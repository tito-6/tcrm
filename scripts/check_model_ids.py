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
    """Check what model IDs exist for our WhatsApp models"""
    
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
        
        print("\n🔍 Searching for WhatsApp model entries in ir.model:")
        
        # Search for all WhatsApp related models
        whatsapp_models = models.execute_kw(db, uid, password,
            'ir.model', 'search_read',
            [[['model', 'like', 'whatsapp%']]],
            {'fields': ['id', 'model', 'name']}
        )
        
        if whatsapp_models:
            print(f"Found {len(whatsapp_models)} WhatsApp models:")
            for model in whatsapp_models:
                print(f"  📋 ID: {model['id']}, Model: {model['model']}, Name: {model['name']}")
        else:
            print("❌ No WhatsApp models found in ir.model!")
            
        print("\n🔍 Checking if models exist in registry (through ir.model):")
        expected_models = [
            'whatsapp.message',
            'whatsapp.conversation', 
            'whatsapp.business.service',
            'whatsapp.message.wizard'
        ]
        
        for model_name in expected_models:
            try:
                model_info = models.execute_kw(db, uid, password,
                    'ir.model', 'search_read',
                    [[['model', '=', model_name]]],
                    {'fields': ['id', 'model', 'name'], 'limit': 1}
                )
                
                if model_info:
                    info = model_info[0]
                    print(f"  ✅ {model_name}: ID={info['id']}, Name='{info['name']}'")
                else:
                    print(f"  ❌ {model_name}: Not found in ir.model")
                    
            except Exception as e:
                print(f"  ❌ {model_name}: Error - {str(e)}")
                
        print("\n🔒 Checking existing access rules:")
        try:
            access_rules = models.execute_kw(db, uid, password,
                'ir.model.access', 'search_read',
                [[['model_id.model', 'like', 'whatsapp%']]],
                {'fields': ['id', 'name', 'model_id', 'group_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink']}
            )
            
            if access_rules:
                print(f"Found {len(access_rules)} access rules:")
                for rule in access_rules:
                    group = rule['group_id'][1] if rule['group_id'] else "All Users"
                    model = rule['model_id'][1] if rule['model_id'] else "Unknown"
                    perms = f"R:{rule['perm_read']} W:{rule['perm_write']} C:{rule['perm_create']} U:{rule['perm_unlink']}"
                    print(f"  🔐 {rule['name']}: {model} - {group} - {perms}")
            else:
                print("❌ No access rules found for WhatsApp models!")
                
        except Exception as e:
            print(f"❌ Error checking access rules: {str(e)}")
            
        print("\n🎯 Checking base.group_user exists:")
        try:
            base_group = models.execute_kw(db, uid, password,
                'res.groups', 'search_read',
                [[['category_id.xml_id', '=', 'base.module_category_user_type'], ['name', '=', 'Internal User']]],
                {'fields': ['id', 'name', 'full_name'], 'limit': 1}
            )
            
            if base_group:
                print(f"  ✅ base.group_user found: ID={base_group[0]['id']}")
            else:
                print("  ❌ base.group_user not found!")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
    
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")

if __name__ == '__main__':
    main()