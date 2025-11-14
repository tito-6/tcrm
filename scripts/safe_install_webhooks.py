#!/usr/bin/env python3
'''
Step-by-step addon installation with UI verification
'''

import odoorpc
import time

HOST = 'localhost'
PORT = 8069
DB = 'crm'
USER = 'admin'
PASSWORD = 'admin'

def connect_odoo():
    odoo = odoorpc.ODOO(HOST, port=PORT)
    odoo.login(DB, USER, PASSWORD)
    return odoo

def install_module(odoo, module_name):
    '''Install a single module and wait for completion'''
    print(f"\n{'='*60}")
    print(f"Installing module: {module_name}")
    print('='*60)
    
    Module = odoo.env['ir.module.module']
    
    # Update module list first
    print("Updating module list...")
    Module.update_list()
    time.sleep(2)
    
    # Find module
    module_ids = Module.search([('name', '=', module_name)])
    if not module_ids:
        print(f"✗ Module '{module_name}' not found")
        return False
    
    module = Module.browse(module_ids[0])
    state = module.state
    
    if state == 'installed':
        print(f"✓ Module already installed")
        return True
    
    print(f"Current state: {state}")
    print("Installing...")
    
    try:
        Module.button_immediate_install([module.id])
        print(f"✓ Installation completed")
        
        # Verify installation
        module.invalidate_cache()
        module = Module.browse(module_ids[0])
        if module.state == 'installed':
            print(f"✓ Verification passed - module is installed")
            return True
        else:
            print(f"⚠ Warning: Module state is {module.state}")
            return False
            
    except Exception as e:
        print(f"✗ Installation failed: {e}")
        return False

def verify_ui_accessible():
    '''Check if Odoo UI is still accessible'''
    import requests
    try:
        response = requests.get(f'http://{HOST}:{PORT}/web/login', timeout=5)
        if response.status_code == 200:
            print("✓ Odoo UI is accessible")
            return True
        else:
            print(f"⚠ UI returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ UI check failed: {e}")
        return False

def main():
    print("="*60)
    print("SAFE ADDON INSTALLATION WIZARD")
    print("="*60)
    
    input("\nPress Enter to verify UI is working before starting...")
    if not verify_ui_accessible():
        print("\n✗ UI is not accessible. Fix this before proceeding.")
        return
    
    print("\n✓ UI is working. Connecting to Odoo...")
    
    try:
        odoo = connect_odoo()
        print(f"✓ Connected to Odoo")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    # Install modules in safe order
    modules = [
        ('meta_leads', 'Meta Lead Management - adds custom fields to CRM'),
        ('webhooks_bridge', 'Webhook Endpoints - exposes /webhooks/meta and /webhooks/google'),
    ]
    
    for module_name, description in modules:
        print(f"\n{description}")
        proceed = input(f"Install '{module_name}'? (y/n): ").strip().lower()
        
        if proceed != 'y':
            print(f"Skipping {module_name}")
            continue
        
        success = install_module(odoo, module_name)
        
        if not success:
            print(f"\n✗ Installation of {module_name} failed")
            retry = input("Continue anyway? (y/n): ").strip().lower()
            if retry != 'y':
                print("Installation aborted")
                return
        
        print("\nVerifying UI accessibility...")
        time.sleep(2)
        
        if not verify_ui_accessible():
            print("\n⚠ WARNING: UI may not be accessible after installing {module_name}")
            print("Check the logs and consider rollback")
            return
        
        print("✓ UI still working after installation")
        input("\nPress Enter to continue to next module...")
    
    print("\n" + "="*60)
    print("INSTALLATION COMPLETE")
    print("="*60)
    print("\nPlease verify:")
    print("1. Open http://localhost:8069 in browser")
    print("2. Login with admin/admin")
    print("3. Check CRM > Leads menu")
    print("4. Look for Meta Lead fields")
    print("5. Check Settings > Technical > Webhooks")

if __name__ == '__main__':
    main()
