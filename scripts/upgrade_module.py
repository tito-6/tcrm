#!/usr/bin/env python3
"""
Upgrade the CRM integration module with new model fields and views
"""
import odoorpc

def upgrade_module():
    """Upgrade the custom CRM integration module"""
    
    # Connect to Odoo
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    
    # Get module
    Module = odoo.env['ir.module.module']
    modules = Module.search([('name', '=', 'custom_crm_integration')])
    
    if modules:
        module = Module.browse(modules[0])
        print(f'Current module state: {module.state}')
        
        if module.state == 'installed':
            # Upgrade the module
            print('Upgrading module...')
            module.button_immediate_upgrade()
            print('✅ Module upgraded successfully!')
            
            # Check fields are created
            Lead = odoo.env['crm.lead']
            field_model = odoo.env['ir.model.fields']
            
            # Check for meta_creative fields
            creative_fields = field_model.search([
                ('model', '=', 'crm.lead'),
                ('name', 'like', 'meta_creative%')
            ])
            
            if creative_fields:
                print(f'✅ Found {len(creative_fields)} creative fields')
                for field_id in creative_fields:
                    field = field_model.browse(field_id)
                    print(f'  - {field.name}: {field.field_description}')
            else:
                print('❌ No creative fields found')
            
        else:
            print(f'Module is not installed, current state: {module.state}')
    else:
        print('❌ Module not found')

if __name__ == '__main__':
    upgrade_module()