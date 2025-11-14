#!/usr/bin/env python3
"""
Create view to display creative data in CRM lead form
"""
import odoorpc

def create_creative_view():
    """Create view to display creative data"""
    
    # Connect to Odoo
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    
    ViewModel = odoo.env['ir.ui.view']
    
    # Check if view already exists
    existing_view = ViewModel.search([('name', '=', 'crm.lead.form.meta.creative')])
    if existing_view:
        print('View already exists, updating...')
        view_id = existing_view[0]
    else:
        view_id = None
    
    # Create view XML for Odoo 17 (without attrs)
    view_arch = '''
<notebook position="inside">
    <page string="Meta Creative" name="meta_creative">
        <group string="Creative Information" col="2">
            <group>
                <field name="meta_creative_id" readonly="1"/>
                <field name="meta_creative_type" readonly="1"/>
                <field name="meta_creative_title" readonly="1"/>
            </group>
            <group>
                <field name="meta_creative_body" readonly="1"/>
                <field name="meta_creative_cta" readonly="1"/>
                <field name="meta_creative_media_url" readonly="1" widget="url"/>
            </group>
        </group>
        
        <separator string="Creative Preview"/>
        <group>
            <div class="alert alert-info" role="alert">
                <strong>Creative Media:</strong> Use the Media URL above to view the creative content.
            </div>
        </group>
    </page>
</notebook>'''
    
    view_data = {
        'name': 'crm.lead.form.meta.creative',
        'model': 'crm.lead',
        'type': 'form',
        'inherit_id': ViewModel.search([('model', '=', 'crm.lead'), ('type', '=', 'form')], limit=1)[0],
        'arch': view_arch,
        'active': True,
    }
    
    try:
        if view_id:
            ViewModel.write([view_id], view_data)
            print(f'✅ Updated view with ID {view_id}')
        else:
            view_id = ViewModel.create(view_data)
            print(f'✅ Created new view with ID {view_id}')
            
        # Check current lead data
        Lead = odoo.env['crm.lead']
        leads = Lead.search([('name', '=', 'Hasan Durak')], limit=1)
        if leads:
            lead = Lead.browse(leads[0])
            print(f'\\nCurrent lead creative data:')
            print(f'  Creative ID: {getattr(lead, "meta_creative_id", "N/A")}')
            print(f'  Creative Type: {getattr(lead, "meta_creative_type", "N/A")}')
            print(f'  Media URL: {getattr(lead, "meta_creative_media_url", "N/A")}')
            print(f'  Title: {getattr(lead, "meta_creative_title", "N/A")}')
            print(f'  Body: {getattr(lead, "meta_creative_body", "N/A")}')
            
    except Exception as e:
        print(f'❌ Error creating/updating view: {e}')

if __name__ == '__main__':
    create_creative_view()