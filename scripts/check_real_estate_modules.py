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
    print(f"✓ Connected to database '{database}'\n")
    
    # Get module model
    Module = odoo.env['ir.module.module']
    
    # Search for real estate, property-related modules
    keywords = ['estate', 'property', 'real_estate', 'realtor', 'rental', 'lease']
    
    print("Searching for Real Estate & Property modules:")
    print("="*60)
    
    found_modules = []
    for keyword in keywords:
        module_ids = Module.search([
            '|', ('name', 'ilike', keyword),
            '|', ('summary', 'ilike', keyword),
            ('description', 'ilike', keyword)
        ])
        
        if module_ids:
            for module_id in module_ids:
                module = Module.browse(module_id)
                if module.name not in [m['name'] for m in found_modules]:
                    found_modules.append({
                        'name': module.name,
                        'summary': module.summary or 'No description',
                        'state': module.state
                    })
    
    if found_modules:
        for mod in found_modules:
            status = "✓ INSTALLED" if mod['state'] == 'installed' else f"  [{mod['state']}]"
            print(f"{status} - {mod['name']}")
            print(f"  → {mod['summary']}")
            print()
    else:
        print("No built-in real estate modules found in Odoo 17 Community Edition.")
        print("\nNote: Real estate functionality may require:")
        print("  1. Custom module development")
        print("  2. Third-party modules from Odoo Apps Store")
        print("  3. Using CRM module with custom fields for properties")
    
    print("="*60)
    
except Exception as e:
    print(f"✗ Error: {e}")
