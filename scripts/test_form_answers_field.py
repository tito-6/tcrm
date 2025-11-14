#!/usr/bin/env python3
"""
Test the Form Answers field availability
"""
import odoorpc

def test_form_answers_field():
    """Test if the meta_form_answers field is available"""
    
    try:
        print("🔗 Connecting to Odoo...")
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        print("✅ Connected to Odoo")
        
        Lead = odoo.env['crm.lead']
        
        # Get field information
        print("\n📋 Checking CRM Lead fields...")
        
        # Check if the field exists
        field_info = Lead.fields_get(['meta_form_answers'])
        
        if 'meta_form_answers' in field_info:
            print("✅ meta_form_answers field found!")
            print(f"   Type: {field_info['meta_form_answers'].get('type')}")
            print(f"   Label: {field_info['meta_form_answers'].get('string')}")
            print(f"   Help: {field_info['meta_form_answers'].get('help')}")
            
            # Test creating a simple lead with the field
            test_data = {
                'name': 'Test Form Answers Lead',
                'meta_form_answers': '=== TEST FORM RESPONSES ===\n\n1. Name: Test User\n2. Email: test@example.com\n3. Phone: +1234567890\n\n--- Form completed with 3 questions ---'
            }
            
            try:
                test_lead = Lead.create(test_data)
                print(f"✅ Successfully created test lead with ID: {test_lead}")
                
                # Read it back to verify
                created_lead = Lead.browse(test_lead)
                print(f"✅ Form Answers field content:")
                print(f"   {created_lead.meta_form_answers}")
                
                # Clean up
                created_lead.unlink()
                print("✅ Test lead cleaned up")
                
                return True
                
            except Exception as e:
                print(f"❌ Error creating test lead: {e}")
                return False
        else:
            print("❌ meta_form_answers field NOT found!")
            print("Available Meta fields:")
            all_fields = Lead.fields_get()
            meta_fields = [f for f in all_fields.keys() if f.startswith('meta_')]
            for field in meta_fields:
                print(f"   - {field}: {all_fields[field].get('string')}")
            return False
            
    except Exception as e:
        print(f"❌ Error connecting to Odoo: {e}")
        return False

if __name__ == '__main__':
    test_form_answers_field()