#!/usr/bin/env python3
"""
Redesign the creative UI using proper Odoo patterns from standard modules
"""
import odoorpc

def redesign_creative_ui():
    """Redesign UI using standard Odoo patterns like product images, partner avatars etc."""
    
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
    
    # Create new UI based on standard Odoo product/partner image patterns
    view_arch = '''
<notebook position="inside">
    <page string="Meta Creative" name="meta_creative">
        <div class="oe_button_box" name="button_box">
            <button name="action_refresh_creative" type="object" class="oe_stat_button" icon="fa-refresh" string="Refresh Creative"/>
        </div>
        
        <sheet>
            <div class="oe_title">
                <h1>
                    <field name="meta_creative_title" placeholder="Creative Title..." readonly="1"/>
                </h1>
            </div>
            
            <div class="o_row">
                <div class="o_cell o_wrap_input flex-grow-1 flex-sm-grow-0 text-break" style="width: 100%;">
                    
                    <!-- Creative Image Preview Section -->
                    <div class="d-flex">
                        <div class="o_cell flex-grow-0 flex-shrink-0 me-3">
                            <field name="meta_creative_media_url" widget="image" 
                                   options="{'preview_image': 'meta_creative_media_url', 'size': [150, 150]}"
                                   readonly="1" class="oe_avatar"/>
                        </div>
                        
                        <div class="o_cell flex-grow-1">
                            <group>
                                <group string="Creative Details" col="2">
                                    <field name="meta_creative_id" readonly="1"/>
                                    <field name="meta_creative_type" readonly="1"/>
                                </group>
                                
                                <group string="Creative Content" col="1">
                                    <field name="meta_creative_body" readonly="1" widget="text"/>
                                    <field name="meta_creative_cta" readonly="1"/>
                                </group>
                                
                                <group string="Media" col="1">
                                    <field name="meta_creative_media_url" readonly="1" widget="url" string="View Full Size"/>
                                </group>
                            </group>
                        </div>
                    </div>
                </div>
            </div>
        </sheet>
    </page>
</notebook>'''
    
    view_data = {'arch': view_arch}
    
    try:
        ViewModel.write([view_id], view_data)
        print('✅ Updated UI with standard Odoo image preview pattern')
        print('   - Uses oe_avatar class for image preview')
        print('   - Sheet layout like product/partner forms')
        print('   - Proper button box for actions')
        print('   - Standard Odoo title layout')
        
    except Exception as e:
        print(f'❌ Error updating view: {e}')
        print('Trying simplified layout...')
        
        # Fallback to simpler but working layout
        simple_arch = '''
<notebook position="inside">
    <page string="Meta Creative" name="meta_creative">
        <group>
            <group string="Creative Preview" col="1">
                <field name="meta_creative_media_url" widget="url" readonly="1" 
                       string="📸 View Creative Image"/>
            </group>
            
            <group string="Creative Information" col="2">
                <group>
                    <field name="meta_creative_id" readonly="1"/>
                    <field name="meta_creative_type" readonly="1"/>
                    <field name="meta_creative_title" readonly="1"/>
                </group>
                <group>
                    <field name="meta_creative_body" readonly="1"/>
                    <field name="meta_creative_cta" readonly="1"/>
                </group>
            </group>
        </group>
    </page>
</notebook>'''
        
        try:
            ViewModel.write([view_id], {'arch': simple_arch})
            print('✅ Updated with simplified but functional layout')
        except Exception as e2:
            print(f'❌ Fallback also failed: {e2}')

if __name__ == '__main__':
    redesign_creative_ui()