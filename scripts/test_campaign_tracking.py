#!/usr/bin/env python3
"""
Test campaign tracking by creating a webhook payload with campaign data
"""
import requests
import json
import time
import odoorpc

def test_campaign_tracking():
    """Test webhook with campaign data"""
    
    # Create a webhook payload with campaign information (simulating real Facebook webhook)
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
                            "leadgen_id": "1160780142100930",  # Use existing lead for testing
                            "page_id": "107962304408790",
                            "form_id": "1731740530826374",
                            "ad_id": "120210000000001",  # Sample ad ID
                            "adgroup_id": "120210000000002",  # Sample adset ID
                            "campaign_id": "120210000000003",  # Sample campaign ID
                            "created_time": int(time.time())
                        }
                    }
                ]
            }
        ]
    }
    
    print("="*70)
    print("TESTING CAMPAIGN TRACKING IN WEBHOOK")
    print("="*70)
    print(f"Lead ID: {webhook_payload['entry'][0]['changes'][0]['value']['leadgen_id']}")
    print(f"Ad ID: {webhook_payload['entry'][0]['changes'][0]['value']['ad_id']}")
    print(f"Ad Set ID: {webhook_payload['entry'][0]['changes'][0]['value']['adgroup_id']}")
    print(f"Campaign ID: {webhook_payload['entry'][0]['changes'][0]['value']['campaign_id']}")
    
    # Check current lead count
    try:
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        Lead = odoo.env['crm.lead']
        before_count = len(Lead.search([]))
        print(f"\n✓ Leads before: {before_count}")
    except Exception as e:
        print(f"✗ Odoo connection error: {e}")
        return
    
    # Send webhook
    webhook_url = "http://localhost:8069/webhooks/meta"
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(webhook_url, json=webhook_payload, headers=headers)
        print(f"✓ Webhook response: {response.status_code} - {response.text}")
        
        # Wait for processing
        time.sleep(3)
        after_count = len(Lead.search([]))
        print(f"✓ Leads after: {after_count}")
        
        if after_count > before_count:
            print("\n✅ New lead created! Checking campaign data...")
            
            # Get the newest lead
            newest_leads = Lead.search([], order='create_date desc', limit=1)
            if newest_leads:
                lead = Lead.browse(newest_leads[0])
                print(f"\n📧 Lead Details:")
                print(f"   Name: {lead.name}")
                print(f"   Email: {getattr(lead, 'email_from', 'N/A')}")
                print(f"   Phone: {getattr(lead, 'phone', 'N/A')}")
                print(f"\n🎯 Campaign Tracking:")
                print(f"   Meta Lead ID: {getattr(lead, 'meta_leadgen_id', 'N/A')}")
                print(f"   Campaign ID: {getattr(lead, 'meta_campaign_id', 'N/A')}")
                print(f"   Campaign Name: {getattr(lead, 'meta_campaign_name', 'N/A')}")
                print(f"   Ad Set ID: {getattr(lead, 'meta_adset_id', 'N/A')}")
                print(f"   Ad Set Name: {getattr(lead, 'meta_adset_name', 'N/A')}")
                print(f"   Ad ID: {getattr(lead, 'meta_ad_id', 'N/A')}")
                print(f"   Ad Name: {getattr(lead, 'meta_ad_name', 'N/A')}")
                print(f"   Source: {getattr(lead, 'meta_source', 'N/A')}")
                print(f"   Medium: {getattr(lead, 'meta_medium', 'N/A')}")
                
                # Check if campaign fields exist
                lead_fields = Lead.fields_get()
                campaign_fields = ['meta_campaign_id', 'meta_campaign_name', 'meta_adset_id', 'meta_adset_name', 'meta_ad_id', 'meta_ad_name', 'meta_source', 'meta_medium']
                
                print(f"\n🔧 Field Status:")
                for field in campaign_fields:
                    if field in lead_fields:
                        print(f"   ✅ {field}: Available")
                    else:
                        print(f"   ❌ {field}: Missing")
        else:
            print("⚠ No new lead created")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

def check_campaign_fields():
    """Check if campaign fields are available in the model"""
    try:
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        Lead = odoo.env['crm.lead']
        
        lead_fields = Lead.fields_get()
        
        print(f"\n{'='*70}")
        print("CAMPAIGN FIELDS STATUS")
        print('='*70)
        
        campaign_fields = {
            'meta_campaign_id': 'Campaign ID',
            'meta_campaign_name': 'Campaign Name', 
            'meta_adset_id': 'Ad Set ID',
            'meta_adset_name': 'Ad Set Name',
            'meta_ad_id': 'Ad ID',
            'meta_ad_name': 'Ad Name',
            'meta_source': 'Source',
            'meta_medium': 'Medium'
        }
        
        for field, description in campaign_fields.items():
            if field in lead_fields:
                field_info = lead_fields[field]
                print(f"✅ {description}: {field_info.get('string', 'Unknown')} ({field_info.get('type', 'Unknown')})")
            else:
                print(f"❌ {description}: Field not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking fields: {e}")
        return False

if __name__ == '__main__':
    # First check if fields are available
    if check_campaign_fields():
        print(f"\n{'='*70}")
        print("TESTING WEBHOOK WITH CAMPAIGN DATA")
        print('='*70)
        # Then test the webhook
        test_campaign_tracking()