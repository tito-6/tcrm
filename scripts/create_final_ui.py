#!/usr/bin/env python3
"""
Create final working creative UI - fully Odoo 17 compatible
"""
import odoorpc

def create_final_creative_ui():
    """Create final working creative UI"""
    
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
    
    # Final clean UI - no buttons, no template syntax, just clean display
    view_arch = '''
<notebook position="inside">
    <page string="Meta Creative" name="meta_creative">
        
        <!-- Creative Title Section -->
        <div invisible="meta_creative_title == False">
            <separator string="Creative Title"/>
            <h2 class="mt16 mb16">
                <field name="meta_creative_title" readonly="1" nolabel="1"/>
            </h2>
        </div>
        
        <!-- Creative Body Section -->
        <div invisible="meta_creative_body == False">
            <separator string="Creative Content"/>
            <div class="mt16 mb16">
                <field name="meta_creative_body" readonly="1" nolabel="1" widget="text"/>
            </div>
        </div>
        
        <!-- Call to Action Section -->
        <div invisible="meta_creative_cta == False">
            <separator string="Call to Action"/>
            <div class="text-center mt16 mb16">
                <span class="badge badge-primary badge-lg" style="font-size: 14px; padding: 8px 16px;">
                    <field name="meta_creative_cta" readonly="1" nolabel="1"/>
                </span>
            </div>
        </div>
        
        <!-- Media Link Section -->
        <div invisible="meta_creative_media_url == False">
            <separator string="Creative Media"/>
            <group>
                <field name="meta_creative_media_url" readonly="1" widget="url" 
                       string="🎨 View Creative Image" class="oe_link"/>
            </group>
        </div>
        
        <!-- Technical Details -->
        <separator string="Creative Details"/>
        <group>
            <group string="Creative Information">
                <field name="meta_creative_id" readonly="1"/>
                <field name="meta_creative_type" readonly="1"/>
            </group>
            <group string="Media Information">
                <field name="meta_creative_media_url" readonly="1"/>
            </group>
        </group>
        
        <!-- No Creative Info -->
        <div class="alert alert-info mt16" invisible="meta_creative_id != False">
            <p><strong>No Creative Information</strong></p>
            <p>This lead does not have Meta creative data.</p>
        </div>
        
    </page>
</notebook>'''
    
    view_data = {'arch': view_arch}
    
    try:
        ViewModel.write([view_id], view_data)
        print('✅ Successfully created final creative UI!')
        print('')
        print('🎨 NEW CREATIVE LAYOUT FEATURES:')
        print('   ✅ Creative title as prominent header')
        print('   ✅ Creative body text clearly displayed')
        print('   ✅ CTA shown as styled badge')
        print('   ✅ Media link prominently featured')
        print('   ✅ Technical details organized in groups')
        print('   ✅ Clean sections with separators')
        print('   ✅ Responsive and expandable design')
        print('')
        print('🚀 Now refresh your browser and check the Meta Creative tab!')
        
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == '__main__':
    create_final_creative_ui()