#!/usr/bin/env python3
"""
Configure Meta webhook for real Facebook pages and test real-time lead capture
"""
import odoorpc
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Your Facebook page IDs
PAGE_IDS = [
    "107962304408790",
    "102054976300193"
]

# Meta credentials
META_APP_ID = os.getenv('META_APP_ID')
META_APP_SECRET = os.getenv('META_APP_SECRET')
META_USER_ACCESS_TOKEN = os.getenv('META_USER_ACCESS_TOKEN')

def get_page_access_token(page_id, user_token):
    """Get page access token for a specific page"""
    url = f"https://graph.facebook.com/v24.0/{page_id}"
    params = {
        'fields': 'access_token',
        'access_token': user_token
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        print(f"Error getting page token for {page_id}: {response.text}")
        return None

def get_page_info(page_id, access_token):
    """Get page information"""
    url = f"https://graph.facebook.com/v24.0/{page_id}"
    params = {
        'fields': 'name,category,about',
        'access_token': access_token
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting page info: {response.text}")
        return None

def get_page_leadgen_forms(page_id, page_token):
    """Get all lead generation forms for a page"""
    url = f"https://graph.facebook.com/v24.0/{page_id}/leadgen_forms"
    params = {
        'access_token': page_token,
        'fields': 'id,name,status,leads_count,created_time'
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get('data', [])
    else:
        print(f"Error getting forms: {response.text}")
        return []

def subscribe_page_to_webhook(page_id, page_token):
    """Subscribe page to webhook for leadgen events"""
    url = f"https://graph.facebook.com/v24.0/{page_id}/subscribed_apps"
    params = {
        'subscribed_fields': 'leadgen',
        'access_token': page_token
    }
    
    response = requests.post(url, params=params)
    print(f"Webhook subscription for page {page_id}: {response.status_code}")
    if response.status_code != 200:
        print(f"Response: {response.text}")
    return response.status_code == 200

def test_webhook_with_odoo():
    """Test webhook endpoint and database connection"""
    print("\n" + "="*60)
    print("TESTING WEBHOOK AND ODOO CONNECTION")
    print("="*60)
    
    # Test Odoo connection
    try:
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        print("✓ Odoo connection successful")
        
        Lead = odoo.env['crm.lead']
        lead_count_before = len(Lead.search([]))
        print(f"✓ Current leads in CRM: {lead_count_before}")
        
    except Exception as e:
        print(f"✗ Odoo connection failed: {e}")
        return False
    
    # Test webhook endpoint
    try:
        webhook_url = "http://localhost:8069/webhooks/meta"
        verify_token = "my_secure_meta_webhook_token_2024"
        
        # Test verification
        verify_response = requests.get(f"{webhook_url}?hub.mode=subscribe&hub.challenge=test123&hub.verify_token={verify_token}")
        if verify_response.text == "test123":
            print("✓ Webhook verification working")
        else:
            print("✗ Webhook verification failed")
            return False
            
    except Exception as e:
        print(f"✗ Webhook test failed: {e}")
        return False
    
    return True

def main():
    print("="*70)
    print("META WEBHOOK CONFIGURATION FOR REAL-TIME LEAD CAPTURE")
    print("="*70)
    
    if not META_USER_ACCESS_TOKEN:
        print("✗ META_USER_ACCESS_TOKEN not found in .env file")
        print("\nTo get a User Access Token:")
        print("1. Go to: https://developers.facebook.com/tools/explorer")
        print("2. Select your app")
        print("3. Generate token with permissions: pages_manage_metadata, pages_read_engagement, leads_retrieval")
        print("4. Add token to .env file as META_USER_ACCESS_TOKEN")
        return
    
    print(f"Using Meta App ID: {META_APP_ID}")
    print(f"User token: {META_USER_ACCESS_TOKEN[:20]}...")
    
    # Test webhook and Odoo first
    if not test_webhook_with_odoo():
        print("\n✗ Basic tests failed. Fix issues before proceeding.")
        return
    
    print(f"\nConfiguring webhook for {len(PAGE_IDS)} pages:")
    
    for page_id in PAGE_IDS:
        print(f"\n{'='*50}")
        print(f"Configuring Page ID: {page_id}")
        print('='*50)
        
        # Get page access token
        page_token = get_page_access_token(page_id, META_USER_ACCESS_TOKEN)
        if not page_token:
            print(f"✗ Failed to get access token for page {page_id}")
            continue
        
        print(f"✓ Page access token obtained")
        
        # Get page info
        page_info = get_page_info(page_id, page_token)
        if page_info:
            print(f"✓ Page Name: {page_info.get('name', 'Unknown')}")
            print(f"✓ Category: {page_info.get('category', 'Unknown')}")
        
        # Get lead forms
        forms = get_page_leadgen_forms(page_id, page_token)
        print(f"✓ Found {len(forms)} lead generation forms")
        
        for form in forms:
            print(f"  - {form['name']} (ID: {form['id']}) - {form.get('leads_count', 0)} leads")
        
        # Subscribe to webhook
        if subscribe_page_to_webhook(page_id, page_token):
            print(f"✓ Page {page_id} subscribed to webhook")
        else:
            print(f"✗ Failed to subscribe page {page_id} to webhook")
    
    print(f"\n{'='*70}")
    print("WEBHOOK CONFIGURATION COMPLETE")
    print('='*70)
    print("\nYour webhook endpoint: http://localhost:8069/webhooks/meta")
    print("Verify token: my_secure_meta_webhook_token_2024")
    print("\nFor external access (Meta webhook), use ngrok:")
    print("1. Check ngrok dashboard: http://localhost:4040")
    print("2. Use the HTTPS URL for Meta webhook configuration")
    print("\nReal-time lead capture is now configured!")
    print("Test by creating a lead on your Facebook forms.")

if __name__ == '__main__':
    main()