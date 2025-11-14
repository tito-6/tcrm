#!/usr/bin/env python3
"""Test WhatsApp models existence in registry directly"""

import odoorpc

try:
    # Connect to Odoo
    print("Connecting to Odoo...")
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    print("✅ Connected to Odoo")

    # Get the registry directly (this bypasses access controls)
    print("\n📋 Checking Model Registry:")
    
    # List all available models in registry
    all_models = list(odoo.env.registry.keys())
    whatsapp_models = [model for model in all_models if 'whatsapp' in model]
    
    print(f"Total models in registry: {len(all_models)}")
    print(f"WhatsApp models found: {len(whatsapp_models)}")
    
    for model in whatsapp_models:
        print(f"  ✅ {model}")
    
    # Check specific models we expect
    expected_models = [
        'whatsapp.message',
        'whatsapp.conversation', 
        'whatsapp.business.service',
        'whatsapp.message.wizard'
    ]
    
    print("\n🎯 Expected Models Check:")
    for model in expected_models:
        if model in all_models:
            print(f"  ✅ {model}")
        else:
            print(f"  ❌ {model} - Missing!")
    
    # Check if we can get model class info (without creating instances)
    print("\n🔍 Model Class Information:")
    for model in whatsapp_models:
        try:
            model_class = odoo.env.registry[model]
            print(f"  {model}: {model_class._description}")
        except Exception as e:
            print(f"  {model}: Error - {e}")
            
    # Try to access the module info
    print("\n📦 Module Information:")
    modules = odoo.env['ir.module.module']
    whatsapp_module = modules.search([('name', '=', 'whatsapp_business_integration')])
    if whatsapp_module:
        module = modules.browse(whatsapp_module[0])
        print(f"  Name: {module.name}")
        print(f"  State: {module.state}")
        print(f"  Version: {module.latest_version}")
        print(f"  Summary: {module.summary}")
        
        # Check dependencies
        dependencies = module.dependencies_id
        print(f"  Dependencies: {len(dependencies)} modules")
        for dep in dependencies:
            print(f"    - {dep.name}: {dep.state}")
    
except Exception as e:
    print(f'Error: {e}')