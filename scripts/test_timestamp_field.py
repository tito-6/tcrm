#!/usr/bin/env python3
"""
Test webhook with proper timestamp to populate the Submitted On field
"""
import requests
import json
import time
import odoorpc

def test_with_timestamp():
    """Test webhook with proper Facebook timestamp"""
    
    # Create a webhook payload with current timestamp (as Facebook would send it)
    current_timestamp = int(time.time())
    
    webhook_payload = {
        "object": "page",
        "entry": [
            {
                "id": "107962304408790",  # Model Sanayi Merkezi
                "time": current_timestamp,
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": "test_timestamp_" + str(current_timestamp),  # Unique test ID
                            "page_id": "107962304408790",
                            "form_id": "1731740530826374",
                            "created_time": current_timestamp  # This is the key for "Submitted On"
                        }
                    }
                ]
            }
        ]
    }
    
    print("Testing webhook with timestamp for 'Submitted On' field...")
    print(f"Test Lead ID: {webhook_payload['entry'][0]['changes'][0]['value']['leadgen_id']}")
    print(f"Timestamp: {current_timestamp} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_timestamp))})")
    
    # Send webhook
    webhook_url = "http://localhost:8069/webhooks/meta"
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(webhook_url, json=webhook_payload, headers=headers)
        print(f"Webhook response: {response.status_code} - {response.text}")
        
        # Wait a moment for processing
        time.sleep(2)
        
        # Check if the lead was created with proper timestamp
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        Lead = odoo.env['crm.lead']
        
        # Find the test lead
        test_leads = Lead.search([('meta_leadgen_id', '=', webhook_payload['entry'][0]['changes'][0]['value']['leadgen_id'])])
        
        if test_leads:
            lead = Lead.browse(test_leads[0])
            print(f"\n✅ Test lead created successfully!")
            print(f"   Name: {lead.name}")
            print(f"   Meta Lead ID: {getattr(lead, 'meta_leadgen_id', 'N/A')}")
            print(f"   Created in CRM: {lead.create_date}")
            print(f"   Submitted On Meta: {getattr(lead, 'meta_submitted_on', 'N/A')}")
            
            submitted_on = getattr(lead, 'meta_submitted_on', None)
            if submitted_on and submitted_on != 'False':
                print(f"   ✅ Submitted On field is working correctly!")
                print(f"   📅 Exact submission time: {submitted_on}")
            else:
                print(f"   ❌ Submitted On field is not populated")
        else:
            print(f"❌ Test lead was not created")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == '__main__':
    test_with_timestamp()