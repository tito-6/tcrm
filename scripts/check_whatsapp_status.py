#!/usr/bin/env python3
"""Check WhatsApp module installation status"""

import odoorpc
import os

try:
    # Connect to Odoo
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')

    # Check module status
    modules = odoo.env['ir.module.module']
    whatsapp_module = modules.search([('name', '=', 'whatsapp_business_integration')])
    
    if whatsapp_module:
        module = modules.browse(whatsapp_module[0])
        print(f'✓ WhatsApp Integration Module - State: {module.state}')
        
        # Check if models exist
        try:
            message_model = odoo.env['whatsapp.message']
            print('✓ WhatsApp Message model found')
        except Exception as e:
            print(f'✗ WhatsApp Message model error: {e}')
            
        try:
            conversation_model = odoo.env['whatsapp.conversation'] 
            print('✓ WhatsApp Conversation model found')
        except Exception as e:
            print(f'✗ WhatsApp Conversation model error: {e}')
            
    else:
        print('✗ Module not found')
        
except Exception as e:
    print(f'Connection error: {e}')