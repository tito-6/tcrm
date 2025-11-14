#!/usr/bin/env python3
"""Update WhatsApp Business Integration module"""

import odoorpc
import os

try:
    # Connect to Odoo
    print("Connecting to Odoo...")
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    print("✓ Connected to Odoo")

    # Update module list
    print("Updating module list...")
    odoo.env['ir.module.module'].update_list()
    
    # Find and upgrade the WhatsApp module
    modules = odoo.env['ir.module.module']
    whatsapp_module = modules.search([('name', '=', 'whatsapp_business_integration')])
    
    if whatsapp_module:
        module = modules.browse(whatsapp_module[0])
        print(f"Found module: {module.name} - State: {module.state}")
        
        if module.state == 'installed':
            print("Upgrading module...")
            module.button_immediate_upgrade()
            print("✓ Module upgraded successfully!")
        else:
            print("Module is not installed")
    else:
        print("✗ Module not found")
        
    # Assign admin user to WhatsApp Manager group
    try:
        admin_user = odoo.env['res.users'].browse(2)  # Admin user ID is typically 2
        whatsapp_manager_group = odoo.env.ref('whatsapp_business_integration.group_whatsapp_manager')
        
        if whatsapp_manager_group.id not in [group.id for group in admin_user.groups_id]:
            admin_user.write({'groups_id': [(4, whatsapp_manager_group.id)]})
            print("✓ Admin user added to WhatsApp Manager group")
        else:
            print("✓ Admin user already in WhatsApp Manager group")
            
    except Exception as e:
        print(f"⚠ Could not assign groups: {e}")
        
except Exception as e:
    print(f'Error: {e}')