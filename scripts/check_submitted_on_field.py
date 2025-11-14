#!/usr/bin/env python3
"""
Check if the "Submitted On" field is working for Meta leads
"""
import odoorpc
from datetime import datetime

def check_submitted_on_field():
    """Check the new meta_submitted_on field"""
    try:
        # Connect to Odoo
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        
        Lead = odoo.env['crm.lead']
        
        # Get Meta leads with the new field
        meta_leads = Lead.search([('meta_leadgen_id', '!=', False)])
        print(f"Found {len(meta_leads)} Meta leads")
        
        # Check recent leads
        recent_leads = Lead.search([('meta_leadgen_id', '!=', False)], order='create_date desc', limit=5)
        
        print("\n" + "="*80)
        print("RECENT META LEADS WITH SUBMITTED ON FIELD")
        print("="*80)
        
        for lead_id in recent_leads:
            lead = Lead.browse(lead_id)
            
            print(f"\n📧 Lead: {lead.name}")
            print(f"   Meta ID: {getattr(lead, 'meta_leadgen_id', 'N/A')}")
            print(f"   Created in CRM: {lead.create_date}")
            print(f"   Submitted On Meta: {getattr(lead, 'meta_submitted_on', 'N/A')}")
            print(f"   Email: {getattr(lead, 'email_from', 'N/A')}")
            print(f"   Phone: {getattr(lead, 'phone', 'N/A')}")
        
        # Check if field exists in model
        lead_fields = Lead.fields_get()
        if 'meta_submitted_on' in lead_fields:
            print(f"\n✅ 'meta_submitted_on' field exists in model")
            field_info = lead_fields['meta_submitted_on']
            print(f"   Type: {field_info.get('type', 'Unknown')}")
            print(f"   String: {field_info.get('string', 'Unknown')}")
            print(f"   Help: {field_info.get('help', 'No help text')}")
        else:
            print(f"\n❌ 'meta_submitted_on' field NOT found in model")
        
        print(f"\n" + "="*80)
        print("FIELD CHECK COMPLETE")
        print("="*80)
        print(f"✓ Access your CRM at: http://localhost:8069/web#action=217&model=crm.lead&view_type=list&cids=1&menu_id=149")
        print(f"✓ Look for the 'Submitted On' column in the list view")
        print(f"✓ New leads will show the exact time they were submitted on Facebook")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking field: {e}")
        return False

if __name__ == '__main__':
    check_submitted_on_field()