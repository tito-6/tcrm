#!/usr/bin/env python3
"""
Test webhook with creative data integration
"""
import requests
import json

def test_webhook_with_creative():
    """Test the webhook endpoint with Meta lead data"""
    
    # Test data simulating Meta webhook
    webhook_data = {
        "object": "page",
        "entry": [{
            "id": "107962304408790",
            "time": 1699612800,
            "changes": [{
                "value": {
                    "leadgen_id": "test_leadgen_123456",
                    "page_id": "107962304408790", 
                    "form_id": "test_form_789",
                    "adgroup_id": "120232150679000651",
                    "ad_id": "120232150679000652",
                    "created_time": "2025-11-10T10:00:00+0000"
                },
                "field": "leadgen"
            }]
        }]
    }
    
    try:
        # Send to webhook
        url = "http://localhost:8069/webhook/meta/leads"
        headers = {
            'Content-Type': 'application/json'
        }
        
        print('Sending webhook data...')
        response = requests.post(url, json=webhook_data, headers=headers)
        
        print(f'Response Status: {response.status_code}')
        print(f'Response Data: {response.text}')
        
        if response.status_code == 200:
            print('✅ Webhook processed successfully!')
            
            # Check if lead was created
            print('\\nLead should be created with creative data from ad ID: 120232150679000652')
            print('Check the CRM lead form to see the "Meta Creative" tab!')
            
        else:
            print('❌ Webhook failed')
            
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == '__main__':
    test_webhook_with_creative()