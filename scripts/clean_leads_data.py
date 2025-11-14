#!/usr/bin/env python3
"""
Clean all existing leads data and prepare for fresh webhook data
"""
import odoorpc

def clean_leads_data():
    """Clean all existing leads to start fresh"""
    try:
        # Connect to Odoo
        print("Connecting to Odoo...")
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        print("✓ Connected")
        
        Lead = odoo.env['crm.lead']
        
        print(f"\n{'='*70}")
        print("CLEANING EXISTING LEADS DATA")
        print('='*70)
        
        # Get all leads
        all_leads = Lead.search([])
        lead_count = len(all_leads)
        
        print(f"📊 Found {lead_count} existing leads")
        
        if lead_count > 0:
            print("🗑️  Deleting all existing leads...")
            
            # Delete all leads
            Lead.unlink(all_leads)
            
            print(f"✅ Deleted {lead_count} leads")
        else:
            print("ℹ️  No leads found to delete")
        
        # Verify cleanup
        remaining_leads = Lead.search([])
        
        print(f"\n{'='*70}")
        print("CLEANUP VERIFICATION")
        print('='*70)
        print(f"📊 Remaining leads: {len(remaining_leads)}")
        
        if len(remaining_leads) == 0:
            print("✅ Cleanup successful - CRM is now empty")
            print("🔄 Ready for fresh webhook data with real campaigns")
        else:
            print("⚠️  Some leads still remain")
            
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning leads: {e}")
        return False

if __name__ == '__main__':
    clean_leads_data()