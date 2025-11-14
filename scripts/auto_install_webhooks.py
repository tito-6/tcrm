#!/usr/bin/env python3
"""Auto-install webhook modules without prompts"""
import odoorpc
import time

HOST = 'localhost'
PORT = 8069
DB = 'crm'
USER = 'admin'
PASSWORD = 'admin'

def install_module(odoo, module_name):
    print(f"\n{'='*60}")
    print(f"Installing module: {module_name}")
    print('='*60)
    
    Module = odoo.env['ir.module.module']
    
    print("Updating module list...")
    Module.update_list()
    time.sleep(2)
    
    module_ids = Module.search([('name', '=', module_name)])
    if not module_ids:
        print(f"✗ Module '{module_name}' not found")
        return False
    
    module = Module.browse(module_ids[0])
    
    if module.state == 'installed':
        print(f"✓ Module already installed")
        return True
    
    print(f"Current state: {module.state}, installing...")
    
    try:
        Module.button_immediate_install([module.id])
        print(f"✓ Installation completed")
        return True
    except Exception as e:
        print(f"✗ Installation failed: {e}")
        return False

print("Connecting to Odoo...")
odoo = odoorpc.ODOO(HOST, port=PORT)
odoo.login(DB, USER, PASSWORD)
print("✓ Connected\n")

# Install modules
install_module(odoo, 'meta_leads')
time.sleep(3)
install_module(odoo, 'webhooks_bridge')

print("\n" + "="*60)
print("INSTALLATION COMPLETE!")
print("="*60)
print("\nVerify at: http://localhost:8069")
print("Login: admin / admin")
