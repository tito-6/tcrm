#!/usr/bin/env python3
"""
Check module installation status and update lead with creative data
"""
import odoorpc
import time

def check_and_update():
    """Check module status and update lead"""
    
    # Connect to Odoo
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    
    # Check module status
    Module = odoo.env['ir.module.module']
    modules = Module.search([('name', '=', 'custom_crm_integration')])
    
    if modules:
        module = Module.browse(modules[0])
        print(f'Module state: {module.state}')
        
        if module.state == 'installed':
            print('✅ Module is installed!')
            
            # Check if fields exist
            Lead = odoo.env['crm.lead']
            leads = Lead.search([('name', '=', 'Hasan Durak')], limit=1)
            
            if leads:
                lead = Lead.browse(leads[0])
                print(f'Lead found: {lead.name}')
                
                # Check if creative fields exist
                try:
                    creative_id = lead.meta_creative_id
                    print(f'Creative ID field exists: {creative_id}')
                    
                    # Try to refresh creative data
                    result = lead.action_refresh_ad_creative()
                    print(f'Refresh result: {result}')
                    
                    # Check preview
                    preview = lead.meta_creative_preview
                    print(f'Preview length: {len(preview or "")} chars')
                    
                except Exception as e:
                    print(f'Error accessing creative fields: {e}')
            else:
                print('❌ Test lead not found')
        else:
            print(f'Module still installing/upgrading: {module.state}')
    else:
        print('❌ Module not found')

if __name__ == '__main__':
    check_and_update()