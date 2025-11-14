#!/usr/bin/env python3
import odoorpc

# Connection details
host = 'localhost'
port = 8069
database = 'crm'
username = 'admin'
password = 'admin'

try:
    print("Connecting to Odoo...")
    odoo = odoorpc.ODOO(host, port=port)
    odoo.login(database, username, password)
    print(f"✓ Connected\n")
    
    # Get module model
    Module = odoo.env['ir.module.module']
    
    # Search for integration modules
    integration_keywords = ['facebook', 'meta', 'google', 'lead', 'form', 'integration', 'webhook']
    
    print("Searching for Lead Integration Modules:")
    print("="*70)
    
    found = {}
    for keyword in integration_keywords:
        module_ids = Module.search([
            '|', ('name', 'ilike', keyword),
            '|', ('summary', 'ilike', keyword),
            ('description', 'ilike', keyword)
        ])
        
        for module_id in module_ids:
            module = Module.browse(module_id)
            if module.name not in found:
                found[module.name] = {
                    'name': module.name,
                    'summary': module.summary or 'No description',
                    'state': module.state,
                    'category': module.category_id.name if module.category_id else 'Other'
                }
    
    # Filter relevant modules
    relevant = []
    for name, info in found.items():
        if any(k in name.lower() for k in ['crm', 'website', 'form', 'social', 'marketing']):
            relevant.append(info)
    
    if relevant:
        for mod in relevant:
            status = "✅ INSTALLED" if mod['state'] == 'installed' else f"❌ [{mod['state']}]"
            print(f"{status} {mod['name']}")
            print(f"   Category: {mod['category']}")
            print(f"   {mod['summary']}")
            print()
    
    print("="*70)
    
    # Check for website forms (which can be used for lead capture)
    print("\n🌐 Website Form Features:")
    form_modules = Module.search([
        ('name', 'in', ['website_form', 'website_crm', 'website_crm_partner_assign'])
    ])
    
    for module_id in form_modules:
        module = Module.browse(module_id)
        status = "✅" if module.state == 'installed' else "❌"
        print(f"{status} {module.name} - {module.state}")
    
except Exception as e:
    print(f"✗ Error: {e}")
