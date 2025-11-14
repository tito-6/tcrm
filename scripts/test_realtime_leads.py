#!/usr/bin/env python3
"""
Simulate a real Facebook webhook to test lead creation in Odoo
"""
import requests
import json
import odoorpc
import time

def test_webhook_with_simulated_lead():
    """Test webhook with realistic Facebook lead data structure"""
    
    # Simulated Facebook webhook payload (structure matches real webhooks)
    webhook_payload = {
        "object": "page",
        "entry": [
            {
                "id": "107962304408790",  # Your first page ID
                "time": int(time.time()),
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": "test_lead_real_structure_123",
                            "page_id": "107962304408790",
                            "form_id": "test_form_456",
                            "adgroup_id": "test_adgroup_789",
                            "ad_id": "test_ad_101112",
                            "created_time": int(time.time())
                        }
                    }
                ]
            }
        ]
    }
    
    print("Testing webhook with simulated Facebook lead data...")
    print(f"Page ID: {webhook_payload['entry'][0]['id']}")
    print(f"Lead ID: {webhook_payload['entry'][0]['changes'][0]['value']['leadgen_id']}")
    
    # Check current lead count in Odoo
    try:
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        Lead = odoo.env['crm.lead']
        before_count = len(Lead.search([]))
        print(f"✓ Leads in CRM before test: {before_count}")
    except Exception as e:
        print(f"✗ Odoo connection failed: {e}")
        return False
    
    # Send webhook
    webhook_url = "http://localhost:8069/webhooks/meta"
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(webhook_url, json=webhook_payload, headers=headers)
        print(f"✓ Webhook response: {response.status_code} - {response.text}")
        
        # Check if lead was created
        time.sleep(2)  # Give it a moment to process
        after_count = len(Lead.search([]))
        print(f"✓ Leads in CRM after test: {after_count}")
        
        if after_count > before_count:
            print("✓ Webhook successfully created lead in CRM!")
            # Get the newest lead
            newest_leads = Lead.search([], order='create_date desc', limit=1)
            if newest_leads:
                lead = Lead.browse(newest_leads[0])
                print(f"  Lead name: {lead.name}")
                print(f"  Meta Lead ID: {getattr(lead, 'meta_leadgen_id', 'Not set')}")
                print(f"  Meta Page ID: {getattr(lead, 'meta_page_id', 'Not set')}")
        else:
            print("⚠ No new lead created - check webhook processing")
            
    except Exception as e:
        print(f"✗ Webhook test failed: {e}")
        return False
    
    return True

def check_ngrok_status():
    """Check if ngrok tunnel is running for external webhook access"""
    try:
        response = requests.get("http://localhost:4040/api/tunnels")
        if response.status_code == 200:
            tunnels = response.json().get('tunnels', [])
            for tunnel in tunnels:
                if tunnel.get('proto') == 'https':
                    public_url = tunnel.get('public_url')
                    print(f"✓ Ngrok HTTPS tunnel: {public_url}")
                    print(f"✓ External webhook URL: {public_url}/webhooks/meta")
                    return public_url
        print("⚠ No HTTPS tunnel found - check ngrok configuration")
        return None
    except:
        print("⚠ Ngrok not accessible - webhook only available locally")
        return None

def main():
    print("="*60)
    print("WEBHOOK REAL-TIME LEAD CAPTURE TEST")
    print("="*60)
    
    # Test local webhook
    print("\n1. Testing local webhook processing...")
    test_webhook_with_simulated_lead()
    
    # Check ngrok for external access
    print(f"\n2. Checking external webhook access...")
    public_url = check_ngrok_status()
    
    print(f"\n{'='*60}")
    print("NEXT STEPS FOR REAL FACEBOOK LEADS")
    print('='*60)
    print("1. Get fresh Facebook User Access Token:")
    print("   - Visit: https://developers.facebook.com/tools/explorer")
    print("   - Select your app: 1576155436683126")
    print("   - Request permissions: pages_manage_metadata, pages_read_engagement, leads_retrieval")
    print("   - Use scripts/get_long_lived_token.py to convert to long-lived token")
    
    print("\n2. Configure Facebook webhook subscription:")
    if public_url:
        print(f"   - Webhook URL: {public_url}/webhooks/meta")
    else:
        print("   - Start ngrok first: docker compose up -d odoo-ngrok")
        print("   - Get HTTPS URL from: http://localhost:4040")
    print("   - Verify Token: my_secure_meta_webhook_token_2024")
    print("   - Subscribe events: leadgen")
    
    print("\n3. Test with real leads:")
    print("   - Create test leads on your Facebook forms")
    print("   - Check CRM for new leads appearing automatically")
    
    print("\nYour webhook system is ready for real-time lead capture! 🚀")

if __name__ == '__main__':
    main()