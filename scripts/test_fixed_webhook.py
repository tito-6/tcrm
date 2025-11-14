#!/usr/bin/env python3
"""
Test the new fixed webhook endpoint
"""
import requests
import json

def test_fixed_webhook():
    """Test the new fixed webhook endpoint"""
    
    # Test data simulating Meta webhook
    webhook_data = {
        "object": "page",
        "entry": [{
            "id": "107962304408790",
            "time": 1699612800,
            "changes": [{
                "value": {
                    "leadgen_id": "test_leadgen_fixed_123",
                    "page_id": "107962304408790", 
                    "form_id": "test_form_fixed_789",
                    "adgroup_id": "120232150679000651",
                    "ad_id": "120232150679000652",
                    "created_time": "2025-11-10T15:30:00+0000"
                },
                "field": "leadgen"
            }]
        }]
    }
    
    try:
        # Send to new fixed webhook
        url = "http://localhost:8069/webhook/meta/fixed"
        headers = {
            'Content-Type': 'application/json'
        }
        
        print('🔧 Testing FIXED webhook endpoint...')
        response = requests.post(url, json=webhook_data, headers=headers)
        
        print(f'Response Status: {response.status_code}')
        print(f'Response Data: {response.text}')
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success', False):
                print('✅ FIXED webhook works perfectly!')
                print('\\n🎉 Lead created with creative data!')
                print('   Check CRM > Leads for the new lead with Meta Creative tab')
            else:
                print(f'❌ Webhook failed: {response_data.get("error")}')
        else:
            print('❌ HTTP error occurred')
            
    except Exception as e:
        print(f'❌ Test failed: {e}')

if __name__ == '__main__':
    test_fixed_webhook()