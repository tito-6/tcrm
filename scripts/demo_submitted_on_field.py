#!/usr/bin/env python3
"""
Update some existing Meta leads with sample "Submitted On" timestamps
This will demonstrate the new field in the CRM list view
"""
import odoorpc
from datetime import datetime, timedelta
import random

def update_sample_leads():
    """Update some leads with sample timestamps"""
    try:
        # Connect to Odoo
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        
        Lead = odoo.env['crm.lead']
        
        # Get some Meta leads
        meta_leads = Lead.search([('meta_leadgen_id', '!=', False)], limit=10)
        
        print(f"Updating {len(meta_leads)} Meta leads with sample 'Submitted On' timestamps...")
        
        updated_count = 0
        
        for i, lead_id in enumerate(meta_leads):
            lead = Lead.browse(lead_id)
            
            # Create a sample timestamp (between 1-30 days ago)
            days_ago = random.randint(1, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            
            sample_timestamp = datetime.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            
            # Update the lead (convert datetime to string for Odoo)
            timestamp_str = sample_timestamp.strftime('%Y-%m-%d %H:%M:%S')
            lead.write({'meta_submitted_on': timestamp_str})
            
            print(f"   ✓ Updated {lead.name} - Submitted On: {sample_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            updated_count += 1
        
        print(f"\n✅ Successfully updated {updated_count} leads!")
        print(f"\n📋 Now check your CRM list view:")
        print(f"   🔗 http://localhost:8069/web#action=217&model=crm.lead&view_type=list&cids=1&menu_id=149")
        print(f"   👀 Look for the 'Submitted On' column showing the timestamps")
        print(f"   ⚙️  If not visible, click the settings icon and enable 'Submitted On'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating leads: {e}")
        return False

if __name__ == '__main__':
    update_sample_leads()