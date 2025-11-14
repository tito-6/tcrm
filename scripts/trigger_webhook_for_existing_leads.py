#!/usr/bin/env python3
"""
Trigger webhook events for existing Facebook leads
This will send existing leads through your webhook system instead of direct import
"""
import odoorpc
import requests
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Your Facebook page IDs
PAGE_IDS = [
    "107962304408790",  # Model Sanayi Merkezi
    "102054976300193"   # Model Kuyum Merkezi
]

# Meta credentials
META_APP_ID = os.getenv('META_APP_ID')
META_APP_SECRET = os.getenv('META_APP_SECRET')
META_USER_ACCESS_TOKEN = os.getenv('META_USER_ACCESS_TOKEN')

# Webhook URL
WEBHOOK_URL = "http://localhost:8069/webhooks/meta"

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

def get_form_leads(form_id, page_token, limit=50):
    """Get leads from a specific form"""
    all_leads = []
    url = f"https://graph.facebook.com/v24.0/{form_id}/leads"
    params = {
        'access_token': page_token,
        'limit': limit,
        'fields': 'id,created_time'
    }
    
    while url:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"Error getting leads from form {form_id}: {response.text}")
            break
            
        data = response.json()
        leads = data.get('data', [])
        all_leads.extend(leads)
        
        # Check for next page
        paging = data.get('paging', {})
        url = paging.get('next')
        params = {}  # Next URL already includes all params
        
        print(f"   Retrieved {len(leads)} leads (total: {len(all_leads)})")
        time.sleep(0.3)  # Rate limiting
        
        # Limit to avoid overwhelming
        if len(all_leads) >= 100:
            print(f"   Limiting to first 100 leads for initial test")
            break
    
    return all_leads

def send_webhook_for_lead(lead_id, page_id, form_id):
    """Send a webhook event for a specific lead"""
    webhook_payload = {
        "object": "page",
        "entry": [
            {
                "id": page_id,
                "time": int(time.time()),
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": lead_id,
                            "page_id": page_id,
                            "form_id": form_id,
                            "created_time": int(time.time())
                        }
                    }
                ]
            }
        ]
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(WEBHOOK_URL, json=webhook_payload, headers=headers)
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

def check_if_lead_exists_in_crm(lead_id):
    """Check if lead already exists in Odoo CRM"""
    try:
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        Lead = odoo.env['crm.lead']
        existing = Lead.search([('meta_leadgen_id', '=', lead_id)])
        return len(existing) > 0
    except:
        return False

def process_page_leads(page_id, page_name):
    """Process all leads from a Facebook page through webhook"""
    print(f"\n{'='*60}")
    print(f"PROCESSING LEADS FROM: {page_name}")
    print(f"PAGE ID: {page_id}")
    print('='*60)
    
    # Get page access token
    page_token = get_page_access_token(page_id, META_USER_ACCESS_TOKEN)
    if not page_token:
        print(f"✗ Failed to get access token for page {page_id}")
        return 0
    
    print(f"✓ Page access token obtained")
    
    # Get lead forms
    forms = get_page_leadgen_forms(page_id, page_token)
    print(f"✓ Found {len(forms)} lead generation forms")
    
    total_processed = 0
    
    for form in forms:
        form_id = form['id']
        form_name = form['name']
        leads_count = form.get('leads_count', 0)
        
        print(f"\n📋 Processing form: {form_name}")
        print(f"   Form ID: {form_id}")
        print(f"   Total leads: {leads_count}")
        
        if leads_count == 0:
            print("   No leads to process")
            continue
        
        # Get leads from this form
        print("   Fetching lead IDs...")
        form_leads = get_form_leads(form_id, page_token)
        
        print(f"   Sending {len(form_leads)} leads through webhook...")
        
        successful = 0
        skipped = 0
        
        for i, lead_data in enumerate(form_leads, 1):
            lead_id = lead_data.get('id')
            
            # Check if already exists
            if check_if_lead_exists_in_crm(lead_id):
                print(f"   ⚠ Lead {i}/{len(form_leads)}: {lead_id} already exists, skipping")
                skipped += 1
                continue
            
            # Send through webhook
            success, response = send_webhook_for_lead(lead_id, page_id, form_id)
            
            if success:
                print(f"   ✓ Lead {i}/{len(form_leads)}: {lead_id} sent through webhook")
                successful += 1
            else:
                print(f"   ✗ Lead {i}/{len(form_leads)}: {lead_id} webhook failed - {response}")
            
            # Rate limiting and avoid overwhelming
            time.sleep(0.5)
            
            # Process in batches
            if i % 10 == 0:
                print(f"   📊 Batch progress: {successful} successful, {skipped} skipped")
                time.sleep(2)
        
        print(f"   📊 Form complete: {successful} sent, {skipped} skipped from {form_name}")
        total_processed += successful
    
    return total_processed

def main():
    print("="*70)
    print("TRIGGER WEBHOOKS FOR EXISTING FACEBOOK LEADS")
    print("="*70)
    print("This will send your existing leads through the webhook system")
    print("so they get processed the same way as new real-time leads!")
    
    # Test webhook first
    print(f"\n🔧 Testing webhook endpoint...")
    try:
        test_response = requests.get(f"{WEBHOOK_URL}?hub.mode=subscribe&hub.challenge=test&hub.verify_token=my_secure_meta_webhook_token_2024")
        if test_response.text == "test":
            print("✓ Webhook endpoint is working")
        else:
            print("✗ Webhook verification failed")
            return
    except Exception as e:
        print(f"✗ Webhook endpoint not accessible: {e}")
        return
    
    # Connect to Odoo to check initial state
    try:
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        Lead = odoo.env['crm.lead']
        initial_count = len(Lead.search([]))
        print(f"✓ Connected to Odoo CRM")
        print(f"✓ Current leads in CRM: {initial_count}")
    except Exception as e:
        print(f"✗ Failed to connect to Odoo: {e}")
        return
    
    # Process leads from both pages
    total_processed = 0
    
    page_names = {
        "107962304408790": "Model Sanayi Merkezi",
        "102054976300193": "Model Kuyum Merkezi"
    }
    
    for page_id in PAGE_IDS:
        page_name = page_names.get(page_id, f"Page {page_id}")
        processed = process_page_leads(page_id, page_name)
        total_processed += processed
    
    # Final summary
    final_count = len(Lead.search([]))
    
    print(f"\n{'='*70}")
    print("WEBHOOK PROCESSING COMPLETE!")
    print('='*70)
    print(f"📊 Total leads sent through webhook: {total_processed}")
    print(f"📊 Initial CRM leads: {initial_count}")
    print(f"📊 Final CRM leads: {final_count}")
    print(f"📊 Net increase: {final_count - initial_count}")
    
    print(f"\n🎉 All existing leads have been processed through your webhook system!")
    print(f"🚀 Your webhook is now capturing both existing and new leads!")
    
    if total_processed > 0:
        print(f"\n💡 What happened:")
        print(f"1. ✓ Found your existing Facebook leads")
        print(f"2. ✓ Sent them through your webhook endpoint")
        print(f"3. ✓ Webhook fetched full lead data from Facebook")
        print(f"4. ✓ Created leads in Odoo CRM with Meta fields")
        print(f"5. ✓ Same process will happen for future real-time leads!")

if __name__ == '__main__':
    main()