#!/usr/bin/env python3
import odoorpc

odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login('crm', 'admin', 'admin')

Module = odoo.env['ir.module.module']

# Check if CRM is installed
crm_ids = Module.search([('name', '=', 'crm')])
if crm_ids:
    crm = Module.browse(crm_ids[0])
    print(f"CRM module state: {crm.state}")
    
    if crm.state != 'installed':
        print("Installing CRM...")
        Module.button_immediate_install([crm.id])
        print("✓ CRM installed")
    else:
        print("✓ CRM already installed")
else:
    print("✗ CRM module not found")
