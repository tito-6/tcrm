#!/usr/bin/env python3
"""
Monitor CRM for new leads in real-time
Run this while testing your Facebook forms to see leads appear instantly
"""
import odoorpc
import time
import json
from datetime import datetime

def connect_to_odoo():
    """Connect to Odoo CRM"""
    try:
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        return odoo
    except Exception as e:
        print(f"Failed to connect to Odoo: {e}")
        return None

def get_lead_details(odoo, lead_id):
    """Get detailed lead information"""
    Lead = odoo.env['crm.lead']
    lead = Lead.browse(lead_id)
    
    details = {
        'id': lead.id,
        'name': lead.name,
        'email': getattr(lead, 'email_from', 'No email'),
        'phone': getattr(lead, 'phone', 'No phone'),
        'source': getattr(lead, 'source_id', {}).get('name', 'Unknown') if hasattr(lead, 'source_id') else 'Unknown',
        'created': lead.create_date,
        'stage': lead.stage_id.name if lead.stage_id else 'No stage',
        'meta_leadgen_id': getattr(lead, 'meta_leadgen_id', 'Not set'),
        'meta_page_id': getattr(lead, 'meta_page_id', 'Not set'),
        'meta_form_id': getattr(lead, 'meta_form_id', 'Not set'),
        'meta_raw_payload': getattr(lead, 'meta_raw_payload', 'Not set')
    }
    
    return details

def monitor_leads():
    """Monitor for new leads and display them in real-time"""
    print("="*70)
    print("REAL-TIME LEAD MONITOR")
    print("="*70)
    print("Watching for new leads in your CRM...")
    print("Create a test lead on your Facebook forms to see it appear here!")
    print("Press Ctrl+C to stop monitoring")
    print("="*70)
    
    odoo = connect_to_odoo()
    if not odoo:
        return
    
    Lead = odoo.env['crm.lead']
    
    # Get initial lead count
    initial_leads = Lead.search([])
    last_count = len(initial_leads)
    
    print(f"Current leads in CRM: {last_count}")
    print("\nWaiting for new leads...")
    
    try:
        while True:
            time.sleep(2)  # Check every 2 seconds
            
            # Get current leads
            current_leads = Lead.search([])
            current_count = len(current_leads)
            
            if current_count > last_count:
                # New lead(s) detected!
                new_lead_count = current_count - last_count
                print(f"\n🎉 {new_lead_count} NEW LEAD(S) DETECTED!")
                print("-" * 50)
                
                # Get the newest leads
                newest_leads = Lead.search([], order='create_date desc', limit=new_lead_count)
                
                for lead_id in newest_leads:
                    details = get_lead_details(odoo, lead_id)
                    
                    print(f"📧 Lead #{details['id']}: {details['name']}")
                    print(f"   Email: {details['email']}")
                    print(f"   Phone: {details['phone']}")
                    print(f"   Stage: {details['stage']}")
                    print(f"   Source: {details['source']}")
                    print(f"   Created: {details['created']}")
                    
                    # Meta-specific fields
                    if details['meta_leadgen_id'] != 'Not set':
                        print(f"   🔹 Meta Lead ID: {details['meta_leadgen_id']}")
                        print(f"   🔹 Meta Page ID: {details['meta_page_id']}")
                        print(f"   🔹 Meta Form ID: {details['meta_form_id']}")
                        print("   🔹 Source: Facebook Lead Ad")
                    
                    print()
                
                last_count = current_count
                print(f"Total leads now: {current_count}")
                print("\nContinuing to monitor...")
            
    except KeyboardInterrupt:
        print(f"\n\nMonitoring stopped.")
        print(f"Final lead count: {current_count}")
        print("Run this script again anytime to monitor for new leads!")

if __name__ == '__main__':
    monitor_leads()