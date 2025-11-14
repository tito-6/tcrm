#!/usr/bin/env python3
"""
Fix existing leads that have "Lead from Meta" names by extracting names from raw payload
"""
import odoorpc
import json
import re

def extract_name_from_payload(raw_payload):
    """Extract name from the raw Facebook payload with improved logic"""
    if not raw_payload:
        return None
    
    try:
        # Parse the raw payload
        if isinstance(raw_payload, str):
            payload_data = json.loads(raw_payload)
        else:
            payload_data = raw_payload
        
        # Extract field data
        field_data = {}
        for item in payload_data.get('field_data', []):
            field_name = item.get('name', '').lower()
            field_values = item.get('values', [])
            if field_values:
                field_data[field_name] = field_values[0]
        
        print(f"    Field data: {field_data}")
        
        # Try various name field combinations
        name_fields = [
            'full_name', 'name', 'ad_name', 'customer_name', 'contact_name',
            'first_name_last_name', 'nombre_completo', 'isim_soyisim'
        ]
        
        for field in name_fields:
            if field_data.get(field):
                return field_data[field].strip()
        
        # If no full name, try combining first and last name
        first_name = field_data.get('first_name') or field_data.get('firstname') or field_data.get('ad') or ''
        last_name = field_data.get('last_name') or field_data.get('lastname') or field_data.get('soyad') or ''
        if first_name or last_name:
            return f"{first_name} {last_name}".strip()
        
        # If still no name, try email username as name
        email = field_data.get('email') or field_data.get('email_address')
        if email and '@' in email:
            email_username = email.split('@')[0]
            # Clean up email username (remove dots, numbers if it looks like a name)
            if not email_username.replace('.', '').replace('_', '').isdigit():
                return email_username.replace('.', ' ').replace('_', ' ').title()
        
        return None
        
    except Exception as e:
        print(f"    Error parsing payload: {e}")
        return None

def fix_lead_names():
    """Fix leads that have generic 'Lead from Meta' names"""
    try:
        # Connect to Odoo
        print("Connecting to Odoo...")
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        print("✓ Connected")
        
        Lead = odoo.env['crm.lead']
        
        # Find leads with generic names
        generic_leads = Lead.search([
            ('name', 'in', ['Lead from Meta', 'Lead from Meta Form']),
            ('meta_raw_payload', '!=', False)
        ])
        
        print(f"\n{'='*60}")
        print(f"FIXING {len(generic_leads)} LEADS WITH GENERIC NAMES")
        print('='*60)
        
        fixed_count = 0
        
        for lead_id in generic_leads:
            lead = Lead.browse(lead_id)
            
            print(f"\n📧 Processing Lead ID {lead.id}: {lead.name}")
            print(f"   Meta ID: {getattr(lead, 'meta_leadgen_id', 'N/A')}")
            print(f"   Email: {getattr(lead, 'email_from', 'N/A')}")
            
            # Extract name from raw payload
            raw_payload = getattr(lead, 'meta_raw_payload', None)
            if raw_payload:
                extracted_name = extract_name_from_payload(raw_payload)
                
                if extracted_name and extracted_name != 'Lead from Meta':
                    # Update the lead name
                    lead.write({
                        'name': extracted_name,
                        'contact_name': extracted_name
                    })
                    
                    print(f"   ✅ Updated name to: {extracted_name}")
                    fixed_count += 1
                else:
                    print(f"   ⚠ Could not extract better name from payload")
            else:
                print(f"   ⚠ No raw payload available")
        
        print(f"\n{'='*60}")
        print(f"NAME FIXING COMPLETE!")
        print('='*60)
        print(f"✅ Fixed {fixed_count} out of {len(generic_leads)} leads")
        print(f"✅ Leads now have proper names extracted from Facebook form data")
        print(f"\n🔗 Check results: http://localhost:8069/web#action=217&model=crm.lead&view_type=list&cids=1&menu_id=149")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing lead names: {e}")
        return False

if __name__ == '__main__':
    fix_lead_names()