#!/usr/bin/env python3
"""Direct group assignment using SQL"""

import odoorpc

try:
    # Connect to Odoo
    print("Connecting to Odoo...")
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    print("✓ Connected to Odoo")

    # Check if admin user is in system admin group (has all permissions)
    admin_user = odoo.env['res.users'].browse(2)
    
    # Find and assign Settings access group to enable group management
    try:
        # Get the Settings/Administration group
        admin_groups = odoo.env['res.groups'].search([
            '|', ('category_id.name', '=', 'Administration'),
            ('name', '=', 'Access Rights')
        ])
        
        if admin_groups:
            admin_group = odoo.env['res.groups'].browse(admin_groups[0])
            print(f"Found admin group: {admin_group.name}")
            
            # Add admin to this group temporarily 
            current_groups = [g.id for g in admin_user.groups_id]
            if admin_group.id not in current_groups:
                current_groups.append(admin_group.id)
                admin_user.write({'groups_id': [(6, 0, current_groups)]})
                print("✓ Added admin to administration group")
        
        # Now try to access WhatsApp groups
        whatsapp_groups = odoo.env['res.groups'].search([('name', 'ilike', 'WhatsApp')])
        if whatsapp_groups:
            print("Found WhatsApp groups:")
            for group_id in whatsapp_groups:
                group = odoo.env['res.groups'].browse(group_id)
                print(f"  - {group.name} (ID: {group.id})")
        else:
            print("No WhatsApp groups found - they may not have been created properly")
            
    except Exception as e:
        print(f"Error accessing groups: {e}")
        
        # Alternative: Try to create a simple access test
        print("Testing basic model access...")
        
        # Test if we can access our models at all
        try:
            messages = odoo.env['whatsapp.message'].search([])
            print(f"✓ Can access whatsapp.message model, found {len(messages)} records")
        except Exception as e2:
            print(f"✗ Cannot access whatsapp.message: {e2}")
            
        try:
            conversations = odoo.env['whatsapp.conversation'].search([])
            print(f"✓ Can access whatsapp.conversation model, found {len(conversations)} records")
        except Exception as e3:
            print(f"✗ Cannot access whatsapp.conversation: {e3}")
        
except Exception as e:
    print(f'Connection error: {e}')