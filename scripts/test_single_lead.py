#!/usr/bin/env python3
"""
Test the fixed webhook with a single lead to verify it's working
"""
import requests
import json
import time
import odoorpc

def test_single_lead():
    """Test webhook with a single lead"""
    
    # Test with a real lead ID from your forms
    webhook_payload = {
        "object": "page",
        "entry": [
            {
                "id": "107962304408790",  # Model Sanayi Merkezi
                "time": int(time.time()),
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": "1160780142100930",  # Real lead ID from your form
                            "page_id": "107962304408790",
                            "form_id": "1731740530826374",
                            "created_time": int(time.time())
                        }
                    }
                ]
            }
        ]
    }
    
    print("Testing fixed webhook with real lead...")
    print(f"Lead ID: {webhook_payload['entry'][0]['changes'][0]['value']['leadgen_id']}")
    
    # Check current lead count
    try:
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        Lead = odoo.env['crm.lead']
        before_count = len(Lead.search([]))
        print(f"Leads before: {before_count}")
    except Exception as e:
        print(f"Odoo connection error: {e}")
        return
    
    # Send webhook
    webhook_url = "http://localhost:8069/webhooks/meta"
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(webhook_url, json=webhook_payload, headers=headers)
        print(f"Webhook response: {response.status_code} - {response.text}")
        
        # Wait and check
        time.sleep(3)
        after_count = len(Lead.search([]))
        print(f"Leads after: {after_count}")
        
        if after_count > before_count:
            print("✅ SUCCESS! Lead was created through webhook!")
            
            # Get the newest lead
            newest_leads = Lead.search([], order='create_date desc', limit=1)
            if newest_leads:
                lead = Lead.browse(newest_leads[0])
                print(f"📧 New lead: {lead.name}")
                print(f"📧 Email: {getattr(lead, 'email_from', 'No email')}")
                print(f"📱 Phone: {getattr(lead, 'phone', 'No phone')}")
                print(f"🆔 Meta Lead ID: {getattr(lead, 'meta_leadgen_id', 'Not set')}")
        else:
            print("❌ Lead was not created - check logs")
            
    except Exception as e:
        print(f"Webhook test failed: {e}")

if __name__ == '__main__':
    test_single_lead()