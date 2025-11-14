#!/usr/bin/env python3
"""
Create an improved creative UI with expandable preview similar to Odoo's standard patterns
"""
import odoorpc

def create_improved_creative_ui():
    """Create improved UI with expandable creative preview"""
    
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
    
    # Create UI similar to how Odoo displays product images or document attachments
    view_arch = '''
<notebook position="inside">
    <page string="Meta Creative" name="meta_creative">
        
        <!-- Creative Preview Section -->
        <group string="Creative Preview" invisible="meta_creative_media_url == False">
            <div class="row">
                <div class="col-md-12">
                    <div class="card mb-3" style="max-width: 100%;">
                        <div class="row g-0">
                            <div class="col-md-4">
                                <div class="text-center p-3">
                                    <a target="_blank" t-att-href="meta_creative_media_url">
                                        <img src="/web/static/src/img/placeholder.png" 
                                             alt="Creative Preview" 
                                             class="img-fluid rounded"
                                             style="max-width: 200px; max-height: 150px; border: 1px solid #dee2e6;"/>
                                        <br/>
                                        <small class="text-muted">Click to view full size</small>
                                    </a>
                                </div>
                            </div>
                            <div class="col-md-8">
                                <div class="card-body">
                                    <h5 class="card-title">
                                        <field name="meta_creative_title" readonly="1" nolabel="1"/>
                                    </h5>
                                    <p class="card-text">
                                        <field name="meta_creative_body" readonly="1" nolabel="1"/>
                                    </p>
                                    <p class="card-text">
                                        <small class="text-muted">
                                            Type: <field name="meta_creative_type" readonly="1" nolabel="1"/> |
                                            CTA: <field name="meta_creative_cta" readonly="1" nolabel="1"/>
                                        </small>
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </group>
        
        <!-- Creative Details Section -->
        <group string="Creative Information">
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
        
        <!-- Placeholder when no creative -->
        <div class="alert alert-info text-center" invisible="meta_creative_media_url != False">
            <h4>No Creative Data Available</h4>
            <p>This lead does not have associated Meta creative information.</p>
        </div>
        
    </page>
</notebook>'''
    
    view_data = {'arch': view_arch}
    
    try:
        ViewModel.write([view_id], view_data)
        print('✅ Updated UI with improved creative card layout')
        print('   - Card-based layout similar to Odoo attachments')
        print('   - Preview placeholder with click-to-view')
        print('   - Bootstrap styling for consistency')
        print('   - Proper responsive design')
        
    except Exception as e:
        print(f'❌ Error updating view: {e}')
        
        # Try even simpler approach focusing on visibility and usability
        basic_arch = '''
<notebook position="inside">
    <page string="Meta Creative" name="meta_creative">
        
        <separator string="Creative Preview" invisible="meta_creative_media_url == False"/>
        <group invisible="meta_creative_media_url == False">
            <div class="text-center">
                <h4><field name="meta_creative_title" readonly="1" nolabel="1"/></h4>
                <p><field name="meta_creative_body" readonly="1" nolabel="1"/></p>
                <p>
                    <a target="_blank" t-att-href="meta_creative_media_url" class="btn btn-primary btn-lg">
                        <i class="fa fa-external-link"/> View Creative Image
                    </a>
                </p>
                <p class="text-muted">
                    <small>
                        Creative ID: <field name="meta_creative_id" readonly="1" nolabel="1"/> |
                        Type: <field name="meta_creative_type" readonly="1" nolabel="1"/>
                    </small>
                </p>
            </div>
        </group>
        
        <separator string="Creative Information"/>
        <group>
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
        
    </page>
</notebook>'''
        
        try:
            ViewModel.write([view_id], {'arch': basic_arch})
            print('✅ Updated with basic but functional creative preview')
            print('   - Centered creative title and body')
            print('   - Large "View Creative Image" button')
            print('   - Clean separation of sections')
        except Exception as e2:
            print(f'❌ Basic version also failed: {e2}')

if __name__ == '__main__':
    create_improved_creative_ui()