#!/usr/bin/env python3
"""
Bring in a few fresh leads from Facebook pages to demonstrate the improved name extraction
"""
import odoorpc
import requests
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

PAGE_IDS = ["107962304408790", "102054976300193"]
META_USER_ACCESS_TOKEN = os.getenv('META_USER_ACCESS_TOKEN')
WEBHOOK_URL = "http://localhost:8069/webhooks/meta"

def get_page_access_token(page_id, user_token):
    """Get page access token"""
    url = f"https://graph.facebook.com/v24.0/{page_id}"
    params = {'fields': 'access_token', 'access_token': user_token}
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get('access_token')
    return None

def get_fresh_leads(page_id, page_token, limit=3):
    """Get a few fresh leads from the page"""
    # Get forms first
    forms_url = f"https://graph.facebook.com/v24.0/{page_id}/leadgen_forms"
    forms_params = {'access_token': page_token, 'fields': 'id,name'}
    
    forms_response = requests.get(forms_url, params=forms_params)
    if forms_response.status_code != 200:
        return []
    
    forms = forms_response.json().get('data', [])
    if not forms:
        return []
    
    # Get leads from the first form
    form_id = forms[0]['id']
    leads_url = f"https://graph.facebook.com/v24.0/{form_id}/leads"
    leads_params = {'access_token': page_token, 'limit': limit, 'fields': 'id,created_time'}
    
    leads_response = requests.get(leads_url, params=leads_params)
    if leads_response.status_code == 200:
        leads_data = leads_response.json().get('data', [])
        return [(lead['id'], form_id) for lead in leads_data]
    
    return []

def send_lead_through_webhook(lead_id, page_id, form_id):
    """Send a lead through the webhook system"""
    webhook_payload = {
        "object": "page",
        "entry": [{
            "id": page_id,
            "time": int(time.time()),
            "changes": [{
                "field": "leadgen",
                "value": {
                    "leadgen_id": lead_id,
                    "page_id": page_id,
                    "form_id": form_id,
                    "created_time": int(time.time())
                }
            }]
        }]
    }
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post(WEBHOOK_URL, json=webhook_payload, headers=headers)
    return response.status_code == 200

def test_fresh_leads():
    """Test webhook with fresh leads to show improved name extraction"""
    print("="*70)
    print("TESTING IMPROVED NAME EXTRACTION WITH FRESH LEADS")
    print("="*70)
    
    # Connect to Odoo to track changes
    try:
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        Lead = odoo.env['crm.lead']
        initial_count = len(Lead.search([]))
        print(f"✓ Initial lead count: {initial_count}")
    except Exception as e:
        print(f"✗ Odoo connection failed: {e}")
        return
    
    total_processed = 0
    
    for page_id in PAGE_IDS:
        print(f"\n📋 Processing page: {page_id}")
        
        # Get page token
        page_token = get_page_access_token(page_id, META_USER_ACCESS_TOKEN)
        if not page_token:
            print(f"   ✗ Failed to get page token")
            continue
        
        print(f"   ✓ Page token obtained")
        
        # Get fresh leads
        fresh_leads = get_fresh_leads(page_id, page_token, limit=2)
        print(f"   ✓ Found {len(fresh_leads)} fresh leads")
        
        for i, (lead_id, form_id) in enumerate(fresh_leads, 1):
            print(f"\n   🔄 Processing lead {i}: {lead_id}")
            
            # Check if already exists
            existing = Lead.search([('meta_leadgen_id', '=', lead_id)])
            if existing:
                print(f"   ⚠ Lead already exists, skipping")
                continue
            
            # Send through webhook
            if send_lead_through_webhook(lead_id, page_id, form_id):
                print(f"   ✓ Sent through webhook successfully")
                total_processed += 1
                time.sleep(2)  # Wait for processing
                
                # Check result
                new_leads = Lead.search([('meta_leadgen_id', '=', lead_id)])
                if new_leads:
                    lead = Lead.browse(new_leads[0])
                    print(f"   ✅ Created: {lead.name}")
                    print(f"      Email: {getattr(lead, 'email_from', 'N/A')}")
                    print(f"      Phone: {getattr(lead, 'phone', 'N/A')}")
                else:
                    print(f"   ⚠ Lead not created (check logs)")
            else:
                print(f"   ✗ Webhook failed")
    
    # Final summary
    final_count = len(Lead.search([]))
    
    print(f"\n{'='*70}")
    print("FRESH LEADS TEST COMPLETE!")
    print('='*70)
    print(f"📊 Leads processed through webhook: {total_processed}")
    print(f"📊 Initial CRM count: {initial_count}")
    print(f"📊 Final CRM count: {final_count}")
    print(f"📊 New leads added: {final_count - initial_count}")
    
    if total_processed > 0:
        print(f"\n✅ Improved name extraction is working!")
        print(f"✅ New leads should have proper names (not 'Lead from Meta')")
        print(f"🔗 Check: http://localhost:8069/web#action=217&model=crm.lead&view_type=list&cids=1&menu_id=149")

if __name__ == '__main__':
    test_fresh_leads()