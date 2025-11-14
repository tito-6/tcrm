#!/usr/bin/env python3
"""
Install and setup the CRM integration module
"""
import odoorpc

def install_module():
    """Install the custom CRM integration module"""
    
    # Connect to Odoo
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    
    # Update module list first
    print('Updating module list...')
    Module = odoo.env['ir.module.module']
    Module.update_list()
    
    # Find and install the module
    modules = Module.search([('name', '=', 'custom_crm_integration')])
    
    if modules:
        module = Module.browse(modules[0])
        print(f'Found module: {module.name} - {module.state}')
        
        if module.state in ['uninstalled', 'uninstallable']:
            print('Installing module...')
            module.button_immediate_install()
            print('✅ Module installed successfully!')
        elif module.state == 'installed':
            print('Module already installed, upgrading...')
            module.button_immediate_upgrade()
            print('✅ Module upgraded successfully!')
        
        # Verify installation
        module = Module.browse(modules[0])  # Refresh
        print(f'Final module state: {module.state}')
        
        if module.state == 'installed':
            # Check fields are created
            field_model = odoo.env['ir.model.fields']
            creative_fields = field_model.search([
                ('model', '=', 'crm.lead'),
                ('name', 'like', 'meta_creative%')
            ])
            
            print(f'Found {len(creative_fields)} creative fields:')
            for field_id in creative_fields:
                field = field_model.browse(field_id)
                print(f'  - {field.name}: {field.field_description}')
        
    else:
        print('❌ Module not found in module list')

if __name__ == '__main__':
    install_module()