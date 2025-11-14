#!/usr/bin/env python3
"""
Add image field to store creative images locally and update UI
"""
import odoorpc

def add_creative_image_field():
    """Add a binary image field for storing creative images"""
    
    # Connect to Odoo
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    
    FieldModel = odoo.env['ir.model.fields']
    Model = odoo.env['ir.model']
    
    # Get crm.lead model
    lead_model = Model.search([('model', '=', 'crm.lead')], limit=1)
    if not lead_model:
        print('❌ CRM Lead model not found')
        return
    
    model_id = lead_model[0]
    
    # Check if image field already exists
    existing = FieldModel.search([
        ('model', '=', 'crm.lead'),
        ('name', '=', 'meta_creative_image')
    ])
    
    if existing:
        print('✅ Creative image field already exists')
    else:
        try:
            # Add binary image field
            field_def = {
                'name': 'meta_creative_image',
                'field_description': 'Meta Creative Image',
                'ttype': 'binary',
                'readonly': True,
                'model_id': model_id,
                'model': 'crm.lead',
                'state': 'manual',
            }
            
            field_id = FieldModel.create(field_def)
            print(f'✅ Created creative image field with ID {field_id}')
        except Exception as e:
            print(f'❌ Error creating image field: {e}')

def update_ui_with_image_preview():
    """Update UI to include proper image preview"""
    
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
    
    # Create improved view with image preview and iframe for external URLs
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
            <div class="o_field_widget">
                <div class="row" invisible="meta_creative_media_url == False">
                    <div class="col-md-6">
                        <div class="card" style="max-width: 350px;">
                            <div class="card-header">
                                <h6 class="card-title mb-0">
                                    <field name="meta_creative_title" readonly="1" nolabel="1"/>
                                </h6>
                            </div>
                            <div class="card-body">
                                <iframe width="300" height="200" frameborder="0" 
                                        t-att-src="meta_creative_media_url"
                                        style="border-radius: 8px;"></iframe>
                                <p class="card-text mt-2">
                                    <field name="meta_creative_body" readonly="1" nolabel="1"/>
                                </p>
                                <div class="text-center" invisible="meta_creative_cta == False">
                                    <span class="btn btn-primary btn-sm" readonly="1">
                                        <field name="meta_creative_cta" readonly="1" nolabel="1"/>
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="text-muted small">
                            <strong>Creative Details:</strong><br/>
                            Type: <field name="meta_creative_type" readonly="1" nolabel="1"/><br/>
                            Creative ID: <field name="meta_creative_id" readonly="1" nolabel="1"/><br/>
                            <a t-att-href="meta_creative_media_url" target="_blank" 
                               class="btn btn-sm btn-outline-secondary mt-2">
                               <i class="fa fa-external-link"/> View Full Size
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </group>
    </page>
</notebook>'''
    
    view_data = {'arch': view_arch}
    
    try:
        ViewModel.write([view_id], view_data)
        print('✅ Updated UI with enhanced creative preview')
        print('   - Card-based layout matching Odoo design')
        print('   - Iframe preview for images')
        print('   - Native button styling for CTA')
        print('   - External link to view full size')
        
    except Exception as e:
        print(f'❌ Error updating view: {e}')
        print('Trying simpler version...')
        
        # Fallback to simpler version without template syntax
        simple_arch = '''
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
            <div class="alert alert-info">
                <strong>Creative Preview:</strong> Click the Media URL above to view the creative content.
                <br/><br/>
                <strong>Creative Type:</strong> <field name="meta_creative_type" readonly="1" nolabel="1"/>
                <br/>
                <strong>Title:</strong> <field name="meta_creative_title" readonly="1" nolabel="1"/>
                <br/>
                <strong>Body:</strong> <field name="meta_creative_body" readonly="1" nolabel="1"/>
                <br/>
                <strong>Call to Action:</strong> <field name="meta_creative_cta" readonly="1" nolabel="1"/>
            </div>
        </group>
    </page>
</notebook>'''
        
        try:
            ViewModel.write([view_id], {'arch': simple_arch})
            print('✅ Updated with simplified creative preview layout')
        except Exception as e2:
            print(f'❌ Fallback also failed: {e2}')

if __name__ == '__main__':
    print('Adding creative image field...')
    add_creative_image_field()
    print('\\nUpdating UI...')
    update_ui_with_image_preview()