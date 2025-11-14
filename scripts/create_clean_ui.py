#!/usr/bin/env python3
"""
Create clean creative UI without template directives - Odoo 17 compatible
"""
import odoorpc

def create_clean_creative_ui():
    """Create clean, functional creative UI without forbidden template syntax"""
    
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
    
    # Clean UI without template syntax, focusing on clear presentation
    view_arch = '''
<notebook position="inside">
    <page string="Meta Creative" name="meta_creative">
        
        <!-- Creative Preview Header -->
        <div class="oe_title" invisible="meta_creative_title == False">
            <h1>
                <field name="meta_creative_title" readonly="1" placeholder="Creative Title"/>
            </h1>
        </div>
        
        <!-- Creative Content Section -->
        <group string="Creative Content" invisible="meta_creative_body == False">
            <field name="meta_creative_body" readonly="1" nolabel="1" 
                   widget="text" class="oe_inline"/>
        </group>
        
        <!-- Call to Action -->
        <group string="Call to Action" invisible="meta_creative_cta == False">
            <div class="text-center">
                <button type="button" class="btn btn-primary btn-lg" disabled="1">
                    <field name="meta_creative_cta" readonly="1" nolabel="1"/>
                </button>
            </div>
        </group>
        
        <!-- Creative Media -->
        <group string="Creative Media" invisible="meta_creative_media_url == False">
            <field name="meta_creative_media_url" readonly="1" widget="url" 
                   string="🎨 View Creative Image"/>
        </group>
        
        <separator string="Creative Details"/>
        
        <!-- Technical Details -->
        <group>
            <group string="Meta Information">
                <field name="meta_creative_id" readonly="1"/>
                <field name="meta_creative_type" readonly="1"/>
            </group>
            <group string="Media Information">
                <field name="meta_creative_media_url" readonly="1" widget="url"/>
            </group>
        </group>
        
        <!-- No Creative Message -->
        <div class="alert alert-info" invisible="meta_creative_id != False">
            <strong>No Creative Information Available</strong>
            <p>This lead does not have Meta creative data associated with it.</p>
        </div>
        
    </page>
</notebook>'''
    
    view_data = {'arch': view_arch}
    
    try:
        ViewModel.write([view_id], view_data)
        print('✅ Successfully updated creative UI!')
        print('   ✅ Clean, expandable layout')
        print('   ✅ Creative title as page header')
        print('   ✅ Styled CTA button preview')
        print('   ✅ Clear media access')
        print('   ✅ Organized technical details')
        print('   ✅ No template syntax - Odoo 17 compatible')
        
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == '__main__':
    create_clean_creative_ui()