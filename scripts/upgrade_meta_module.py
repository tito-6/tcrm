#!/usr/bin/env python3
"""
Upgrade meta_leads module to add the new "Submitted On" field
"""
import odoorpc

def upgrade_modules():
    """Upgrade meta_leads module"""
    try:
        # Connect to Odoo
        print("Connecting to Odoo...")
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        print("✓ Connected")
        
        # Get module model
        Module = odoo.env['ir.module.module']
        
        print("\n" + "="*60)
        print("UPGRADING MODULE: meta_leads")
        print("="*60)
        
        # Find meta_leads module
        module_ids = Module.search([('name', '=', 'meta_leads')])
        if not module_ids:
            print("✗ Module 'meta_leads' not found")
            return False
        
        module = Module.browse(module_ids[0])
        print(f"Current state: {module.state}")
        
        # Upgrade the module
        print("Upgrading module...")
        module.button_immediate_upgrade()
        print("✓ Module upgraded successfully")
        
        print("\n" + "="*60)
        print("UPGRADING MODULE: webhooks_bridge")
        print("="*60)
        
        # Find webhooks_bridge module
        module_ids = Module.search([('name', '=', 'webhooks_bridge')])
        if not module_ids:
            print("✗ Module 'webhooks_bridge' not found")
            return False
        
        module = Module.browse(module_ids[0])
        print(f"Current state: {module.state}")
        
        # Upgrade the module
        print("Upgrading module...")
        module.button_immediate_upgrade()
        print("✓ Module upgraded successfully")
        
        print("\n" + "="*60)
        print("UPGRADE COMPLETE!")
        print("="*60)
        print("✓ meta_leads module upgraded with 'Submitted On' field")
        print("✓ webhooks_bridge module upgraded")
        print("✓ New field will be visible in CRM lead list view")
        print("\nCheck your CRM at: http://localhost:8069/web#action=217&model=crm.lead&view_type=list&cids=1&menu_id=149")
        
        return True
        
    except Exception as e:
        print(f"✗ Error upgrading modules: {e}")
        return False

if __name__ == '__main__':
    upgrade_modules()