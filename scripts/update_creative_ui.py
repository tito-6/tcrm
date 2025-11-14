#!/usr/bin/env python3
"""
Update the UI view with proper Odoo image widgets and native styling
"""
import odoorpc

def update_creative_view():
    """Update view to use proper Odoo image widgets"""
    
    # Connect to Odoo
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    
    ViewModel = odoo.env['ir.ui.view']
    
    # Find the existing view
    existing_view = ViewModel.search([('name', '=', 'crm.lead.form.meta.creative')])
    if not existing_view:
        print('❌ View not found')
        return
    
    view_id = existing_view[0]
    
    # Create improved view XML with native Odoo styling
    view_arch = '''
<notebook position="inside">
    <page string="Meta Creative" name="meta_creative">
        <group string="Creative Information">
            <group>
                <field name="meta_creative_id" readonly="1"/>
                <field name="meta_creative_type" readonly="1"/>
                <field name="meta_creative_title" readonly="1"/>
            </group>
            <group>
                <field name="meta_creative_body" readonly="1"/>
                <field name="meta_creative_cta" readonly="1"/>
                <field name="meta_creative_media_url" widget="url" readonly="1"/>
            </group>
        </group>
        
        <separator string="Creative Preview"/>
        <group>
            <field name="meta_creative_media_url" widget="image" readonly="1" 
                   options="{'size': [300, 200]}" nolabel="1"
                   invisible="meta_creative_media_url == False"/>
        </group>
    </page>
</notebook>'''
    
    view_data = {
        'arch': view_arch,
    }
    
    try:
        ViewModel.write([view_id], view_data)
        print(f'✅ Updated view with native Odoo image widget')
        print('   - Uses standard Odoo image widget for preview')
        print('   - Automatic image resizing to 300x200')
        print('   - Native Odoo styling and responsive design')
        
    except Exception as e:
        print(f'❌ Error updating view: {e}')

if __name__ == '__main__':
    update_creative_view()