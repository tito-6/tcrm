#!/usr/bin/env python3
"""
Force install the module and check for errors
"""
import odoorpc

def force_install():
    """Force install the module"""
    
    try:
        # Connect to Odoo
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        
        # Get module
        Module = odoo.env['ir.module.module']
        modules = Module.search([('name', '=', 'custom_crm_integration')])
        
        if modules:
            module = Module.browse(modules[0])
            print(f'Module state: {module.state}')
            
            # Try to install
            if module.state in ['uninstalled', 'to install']:
                print('Forcing installation...')
                
                # First update module list
                Module.update_list()
                
                # Refresh module record
                module = Module.browse(modules[0])
                print(f'After update - Module state: {module.state}')
                
                # Install
                module.button_immediate_install()
                
                # Wait and check
                import time
                time.sleep(5)
                
                module = Module.browse(modules[0])
                print(f'Final state: {module.state}')
                
                if module.state == 'installed':
                    print('✅ Module successfully installed!')
                    
                    # Test fields
                    Lead = odoo.env['crm.lead']
                    leads = Lead.search([('name', '=', 'Hasan Durak')], limit=1)
                    
                    if leads:
                        lead = Lead.browse(leads[0])
                        
                        # Check if we can access new fields
                        try:
                            fields_to_check = [
                                'meta_creative_id',
                                'meta_creative_type', 
                                'meta_creative_media_url',
                                'meta_creative_preview'
                            ]
                            
                            for field in fields_to_check:
                                try:
                                    value = getattr(lead, field, None)
                                    print(f'✅ {field}: {"OK" if hasattr(lead, field) else "NOT FOUND"}')
                                except Exception as e:
                                    print(f'❌ {field}: {e}')
                        
                        except Exception as e:
                            print(f'Error accessing lead fields: {e}')
                
            elif module.state == 'installed':
                print('Module already installed')
            else:
                print(f'Unexpected module state: {module.state}')
                
        else:
            print('Module not found')
            
    except Exception as e:
        print(f'Connection error: {e}')

if __name__ == '__main__':
    force_install()