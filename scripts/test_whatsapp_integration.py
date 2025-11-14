#!/usr/bin/env python3
"""Test WhatsApp Integration - Simple API Test"""

import odoorpc
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='.env')

try:
    # Connect to Odoo
    print("🚀 Testing WhatsApp Business Integration")
    print("=" * 50)
    
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    print("✅ Connected to Odoo CRM")

    # Test environment variables
    print("\n📋 Environment Configuration:")
    meta_token = os.getenv('META_USER_ACCESS_TOKEN')
    whatsapp_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
    phone_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    business_id = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID')
    
    print(f"  Meta Token: {'✅ Set' if meta_token else '❌ Missing'}")
    print(f"  WhatsApp Token: {'✅ Set' if whatsapp_token else '❌ Missing'}")
    print(f"  Phone Number ID: {'✅' if phone_id else '❌'} {phone_id or 'Missing'}")
    print(f"  Business Account ID: {'✅' if business_id else '❌'} {business_id or 'Missing'}")
    
    # Test module status
    print("\n🔧 Module Status:")
    modules = odoo.env['ir.module.module']
    whatsapp_module = modules.search([('name', '=', 'whatsapp_business_integration')])
    if whatsapp_module:
        module = modules.browse(whatsapp_module[0])
        print(f"  WhatsApp Integration: ✅ {module.state}")
    else:
        print("  WhatsApp Integration: ❌ Not found")
    
    # Test models accessibility
    print("\n🗃️ Model Access Test:")
    
    # Test with basic operations that don't require group permissions
    try:
        # Check if models exist in registry
        if 'whatsapp.message' in odoo.env.registry:
            print("  whatsapp.message: ✅ Model exists")
        else:
            print("  whatsapp.message: ❌ Model not in registry")
            
        if 'whatsapp.conversation' in odoo.env.registry:
            print("  whatsapp.conversation: ✅ Model exists")  
        else:
            print("  whatsapp.conversation: ❌ Model not in registry")
            
        if 'whatsapp.business.service' in odoo.env.registry:
            print("  whatsapp.business.service: ✅ Model exists")
        else:
            print("  whatsapp.business.service: ❌ Model not in registry")
            
    except Exception as e:
        print(f"  Model registry error: ❌ {e}")
    
    # Test API connectivity (basic test without creating records)
    print("\n🌐 WhatsApp API Configuration Test:")
    if meta_token and phone_id:
        import requests
        try:
            url = f"https://graph.facebook.com/v21.0/{phone_id}"
            headers = {'Authorization': f'Bearer {meta_token}'}
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"  API Connection: ✅ Phone number verified")
                print(f"  Display Name: {data.get('display_phone_number', 'N/A')}")
                print(f"  Verified Name: {data.get('verified_name', 'N/A')}")
            else:
                print(f"  API Connection: ⚠️  Status {response.status_code}")
                print(f"  Response: {response.text[:100]}...")
                
        except Exception as e:
            print(f"  API Connection: ❌ {str(e)}")
    else:
        print("  API Connection: ⚠️  Missing credentials")
    
    print("\n🎯 Integration Status:")
    
    # Count key components
    component_count = 0
    if meta_token: component_count += 1
    if phone_id: component_count += 1
    if whatsapp_module: component_count += 1
    if 'whatsapp.message' in odoo.env.registry: component_count += 1
    
    status = "🟢 Ready" if component_count >= 3 else "🟡 Partial" if component_count >= 2 else "🔴 Issues"
    print(f"  Overall Status: {status} ({component_count}/4 components working)")
    
    print(f"\n{'=' * 50}")
    print("Integration test completed!")
        
except Exception as e:
    print(f'❌ Connection error: {e}')