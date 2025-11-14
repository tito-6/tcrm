#!/usr/bin/env python3
"""Assign admin user to WhatsApp groups"""

import odoorpc

try:
    # Connect to Odoo
    print("Connecting to Odoo...")
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    print("✓ Connected to Odoo")

    # Find the admin user (usually ID 2)
    users = odoo.env['res.users']
    admin_user = users.browse(2)
    print(f"Found admin user: {admin_user.name}")
    
    # Find WhatsApp groups
    groups = odoo.env['res.groups']
    
    try:
        # Try to find the groups by XML ID
        whatsapp_user_group_id = odoo.env['ir.model.data'].xmlid_to_res_id('whatsapp_business_integration.group_whatsapp_user')
        whatsapp_manager_group_id = odoo.env['ir.model.data'].xmlid_to_res_id('whatsapp_business_integration.group_whatsapp_manager')
        
        print(f"WhatsApp User Group ID: {whatsapp_user_group_id}")
        print(f"WhatsApp Manager Group ID: {whatsapp_manager_group_id}")
        
        # Get current groups
        current_group_ids = [group.id for group in admin_user.groups_id]
        print(f"Current admin groups: {len(current_group_ids)} groups")
        
        # Add WhatsApp groups if not already assigned
        new_group_ids = current_group_ids.copy()
        
        if whatsapp_user_group_id not in new_group_ids:
            new_group_ids.append(whatsapp_user_group_id)
            print("Adding WhatsApp User group")
            
        if whatsapp_manager_group_id not in new_group_ids:
            new_group_ids.append(whatsapp_manager_group_id)
            print("Adding WhatsApp Manager group")
        
        # Update user groups
        admin_user.write({'groups_id': [(6, 0, new_group_ids)]})
        print("✓ Admin user groups updated successfully!")
        
        # Verify
        updated_admin = users.browse(2)
        updated_group_names = [group.name for group in updated_admin.groups_id]
        print(f"Updated groups: {updated_group_names}")
        
    except Exception as e:
        print(f"Group assignment error: {e}")
        
        # Try finding groups by name instead
        print("Trying to find groups by name...")
        whatsapp_groups = groups.search([('name', 'like', 'WhatsApp')])
        for group in groups.browse(whatsapp_groups):
            print(f"Found group: {group.name} (ID: {group.id})")
        
except Exception as e:
    print(f'Error: {e}')