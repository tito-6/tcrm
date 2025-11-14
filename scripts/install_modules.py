#!/usr/bin/env python3
import odoorpc

# Connection details
host = 'localhost'
port = 8069
database = 'crm'
username = 'admin'
password = 'admin'

# Modules to install - Real Estate, CRM, Sales, HR, etc.
modules_to_install = [
    'crm',                    # CRM - Leads & Opportunities
    'sale_management',        # Sales Management
    'sale_crm',              # CRM & Sales Integration
    'hr',                    # Employee Management
    'hr_recruitment',        # Recruitment
    'hr_attendance',         # Attendance
    'hr_holidays',           # Time Off
    'hr_expense',            # Expenses
    'project',               # Project Management
    'contacts',              # Contacts
    'calendar',              # Calendar
    'note',                  # Notes
    'mail',                  # Discuss (Mail)
    'website',               # Website Builder
    'website_crm',           # Website CRM Integration
]

try:
    print("Connecting to Odoo...")
    odoo = odoorpc.ODOO(host, port=port)
    odoo.login(database, username, password)
    print(f"✓ Connected to database '{database}' as '{username}'")
    
    # Get module model
    Module = odoo.env['ir.module.module']
    
    installed_count = 0
    already_installed = 0
    failed = []
    
    for module_name in modules_to_install:
        print(f"\nProcessing module: {module_name}")
        
        # Search for the module
        module_ids = Module.search([('name', '=', module_name)])
        
        if not module_ids:
            print(f"  ⚠ Module '{module_name}' not found")
            failed.append(module_name)
            continue
        
        module = Module.browse(module_ids[0])
        
        if module.state == 'installed':
            print(f"  ✓ Already installed")
            already_installed += 1
        elif module.state in ['uninstalled', 'to install']:
            print(f"  → Installing...")
            try:
                Module.button_immediate_install([module.id])
                print(f"  ✓ Installed successfully")
                installed_count += 1
            except Exception as e:
                print(f"  ✗ Installation failed: {e}")
                failed.append(module_name)
        else:
            print(f"  ⚠ Module state: {module.state}")
    
    print("\n" + "="*60)
    print(f"Installation Summary:")
    print(f"  - Newly installed: {installed_count}")
    print(f"  - Already installed: {already_installed}")
    print(f"  - Failed: {len(failed)}")
    if failed:
        print(f"  - Failed modules: {', '.join(failed)}")
    print("="*60)
    
except Exception as e:
    print(f"✗ Error: {e}")
    print("\nMake sure:")
    print("  1. Odoo is running (docker compose ps)")
    print("  2. Database 'crm' exists")
    print("  3. Login credentials are correct")
    print("  4. OdooRPC is installed (pip install odoorpc)")
