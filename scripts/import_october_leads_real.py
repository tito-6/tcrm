#!/usr/bin/env python3
"""
Import ALL leads from October 2025 with real campaign data from Facebook
Uses existing Meta credentials from .env file
"""
import odoorpc
import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
import time

load_dotenv()

# Your Facebook page IDs (Model Sanayi pages)
PAGE_IDS = [
    "61557077311249",    # Model Sanayi main page
    "107962304408790",   # Additional page 1  
    "102054976300193"    # Additional page 2
]

# Meta credentials from .env
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
        print(f"⚠️ Error getting page token for {page_id}: {response.text}")
        return None

def get_october_leads_for_page(page_id, page_token):
    """Fetch all October 2025 leads for a specific page"""
    
    print(f"\n📄 Processing page: {page_id}")
    
    # October 2025 date range (Unix timestamps)
    october_start = int(datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp())
    october_end = int(datetime(2025, 10, 31, 23, 59, 59, tzinfo=timezone.utc).timestamp())
    
    # Get all lead forms for this page
    forms_url = f"https://graph.facebook.com/v24.0/{page_id}/leadgen_forms"
    forms_params = {
        'access_token': page_token,
        'fields': 'id,name,status,created_time'
    }
    
    forms_response = requests.get(forms_url, params=forms_params)
    
    if forms_response.status_code != 200:
        print(f"   ❌ Error fetching forms: {forms_response.text}")
        return []
        
    forms_data = forms_response.json()
    forms = forms_data.get('data', [])
    
    print(f"   📋 Found {len(forms)} lead forms")
    
    all_leads = []
    
    for form in forms:
        form_id = form['id']
        form_name = form['name']
        
        print(f"   📝 Processing form: {form_name}")
        
        # Get leads for this form in October
        leads_url = f"https://graph.facebook.com/v24.0/{form_id}/leads"
        leads_params = {
            'access_token': page_token,
            'fields': 'id,created_time,field_data,ad_id,adset_id,campaign_id,form_id,is_organic',
            'filtering': json.dumps([
                {
                    'field': 'time_created',
                    'operator': 'GREATER_THAN',
                    'value': october_start
                },
                {
                    'field': 'time_created', 
                    'operator': 'LESS_THAN',
                    'value': october_end
                }
            ]),
            'limit': 500
        }
        
        leads_response = requests.get(leads_url, params=leads_params)
        
        if leads_response.status_code != 200:
            print(f"      ❌ Error fetching leads: {leads_response.text}")
            continue
            
        leads_data = leads_response.json()
        form_leads = leads_data.get('data', [])
        
        print(f"      ✅ Found {len(form_leads)} October leads")
        
        # Add page_id and form info to each lead
        for lead in form_leads:
            lead['page_id'] = page_id
            lead['form_name'] = form_name
            
        all_leads.extend(form_leads)
        
        # Handle pagination
        while 'paging' in leads_data and 'next' in leads_data['paging']:
            next_url = leads_data['paging']['next']
            leads_response = requests.get(next_url)
            
            if leads_response.status_code == 200:
                leads_data = leads_response.json()
                if 'data' in leads_data:
                    form_leads = leads_data['data']
                    # Add page_id and form info
                    for lead in form_leads:
                        lead['page_id'] = page_id
                        lead['form_name'] = form_name
                    all_leads.extend(form_leads)
                    print(f"      📄 Fetched {len(form_leads)} more leads...")
                else:
                    break
            else:
                break
                
            time.sleep(0.3)  # Rate limiting
    
    return all_leads

def fetch_campaign_data(lead):
    """Fetch real campaign data from Facebook for a lead"""
    campaign_data = {
        'campaign_id': '',
        'campaign_name': '',
        'adset_id': '',
        'adset_name': '',
        'ad_id': '',
        'ad_name': '',
        'source': 'facebook',
        'medium': 'facebook_ads'
    }
    
    try:
        # Get campaign data if available
        if lead.get('campaign_id'):
            campaign_url = f"https://graph.facebook.com/v24.0/{lead['campaign_id']}"
            campaign_params = {
                'access_token': META_USER_ACCESS_TOKEN,
                'fields': 'id,name,status,objective'
            }
            
            campaign_response = requests.get(campaign_url, params=campaign_params)
            
            if campaign_response.status_code == 200:
                campaign_info = campaign_response.json()
                campaign_data['campaign_id'] = campaign_info.get('id', '')
                campaign_data['campaign_name'] = campaign_info.get('name', '')
        
        # Get ad set data if available
        if lead.get('adset_id'):
            adset_url = f"https://graph.facebook.com/v24.0/{lead['adset_id']}"
            adset_params = {
                'access_token': META_USER_ACCESS_TOKEN,
                'fields': 'id,name,status,targeting'
            }
            
            adset_response = requests.get(adset_url, params=adset_params)
            
            if adset_response.status_code == 200:
                adset_info = adset_response.json()
                campaign_data['adset_id'] = adset_info.get('id', '')
                campaign_data['adset_name'] = adset_info.get('name', '')
        
        # Get ad data if available
        if lead.get('ad_id'):
            ad_url = f"https://graph.facebook.com/v24.0/{lead['ad_id']}"
            ad_params = {
                'access_token': META_USER_ACCESS_TOKEN,
                'fields': 'id,name,status'
            }
            
            ad_response = requests.get(ad_url, params=ad_params)
            
            if ad_response.status_code == 200:
                ad_info = ad_response.json()
                campaign_data['ad_id'] = ad_info.get('id', '')
                campaign_data['ad_name'] = ad_info.get('name', '')
        
        # Small delay to respect rate limits
        time.sleep(0.1)
                
    except Exception as e:
        print(f"      ⚠️ Error fetching campaign data: {e}")
    
    return campaign_data

def import_october_leads():
    """Main function to import all October leads"""
    
    print("="*80)
    print("🚀 IMPORTING ALL OCTOBER 2025 LEADS WITH REAL CAMPAIGN DATA")
    print("="*80)
    
    # Verify credentials
    if not META_USER_ACCESS_TOKEN:
        print("❌ META_USER_ACCESS_TOKEN not found in .env file")
        return False
    
    print(f"📅 Target Period: October 1-31, 2025")
    print(f"📄 Pages to process: {len(PAGE_IDS)}")
    
    # Connect to Odoo
    try:
        print(f"\n🔗 Connecting to Odoo...")
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        print("✅ Connected to Odoo")
        
        Lead = odoo.env['crm.lead']
        
    except Exception as e:
        print(f"❌ Error connecting to Odoo: {e}")
        return False
    
    # Process each page
    all_leads = []
    total_created = 0
    
    for page_id in PAGE_IDS:
        print(f"\n{'='*60}")
        print(f"PROCESSING PAGE: {page_id}")
        print('='*60)
        
        # Get page access token
        page_token = get_page_access_token(page_id, META_USER_ACCESS_TOKEN)
        
        if not page_token:
            print(f"❌ Could not get page token for {page_id}")
            continue
        
        # Get October leads for this page
        page_leads = get_october_leads_for_page(page_id, page_token)
        
        if not page_leads:
            print(f"   ℹ️ No October leads found for page {page_id}")
            continue
        
        print(f"\n📊 Processing {len(page_leads)} leads from page {page_id}")
        
        page_created = 0
        
        for i, lead in enumerate(page_leads, 1):
            print(f"\n   📧 Lead {i}/{len(page_leads)}")
            print(f"      Meta ID: {lead.get('id')}")
            print(f"      Created: {lead.get('created_time')}")
            print(f"      Form: {lead.get('form_name', 'Unknown')}")
            
            # Check if lead already exists
            existing_lead = Lead.search([('meta_leadgen_id', '=', lead.get('id'))])
            
            if existing_lead:
                print(f"      ⚠️ Lead already exists, skipping...")
                continue
            
            # Extract lead data from field_data
            field_data = lead.get('field_data', [])
            lead_info = {}
            
            for field in field_data:
                field_name = field.get('name', '').lower()
                field_values = field.get('values', [])
                field_value = field_values[0] if field_values else ''
                
                if field_name in ['full_name', 'name']:
                    lead_info['name'] = field_value
                elif field_name in ['email']:
                    lead_info['email'] = field_value
                elif field_name in ['phone_number', 'phone']:
                    lead_info['phone'] = field_value
                elif field_name in ['city']:
                    lead_info['city'] = field_value
            
            # Fetch real campaign data
            print(f"      🎯 Fetching campaign data...")
            campaign_data = fetch_campaign_data(lead)
            
            if campaign_data['campaign_name']:
                print(f"      ✅ Campaign: {campaign_data['campaign_name']}")
            if campaign_data['adset_name']:
                print(f"      ✅ Ad Set: {campaign_data['adset_name']}")
            if campaign_data['ad_name']:
                print(f"      ✅ Ad: {campaign_data['ad_name']}")
            
            # Create lead in Odoo CRM
            crm_lead_data = {
                'name': lead_info.get('name', 'Lead from Meta'),
                'email_from': lead_info.get('email', ''),
                'phone': lead_info.get('phone', ''),
                'city': lead_info.get('city', ''),
                'meta_leadgen_id': lead.get('id'),
                'meta_form_id': lead.get('form_id'),
                'description': f"October 2025 lead from Facebook page {page_id} - Form: {lead.get('form_name', 'Unknown')}",
                
                # Real campaign tracking data
                'meta_campaign_id': campaign_data['campaign_id'],
                'meta_campaign_name': campaign_data['campaign_name'],
                'meta_adset_id': campaign_data['adset_id'],
                'meta_adset_name': campaign_data['adset_name'],
                'meta_ad_id': campaign_data['ad_id'],
                'meta_ad_name': campaign_data['ad_name'],
                'meta_source': campaign_data['source'],
                'meta_medium': campaign_data['medium']
            }
            
            try:
                new_lead = Lead.create(crm_lead_data)
                print(f"      ✅ Created CRM lead ID: {new_lead}")
                page_created += 1
                total_created += 1
                
            except Exception as e:
                print(f"      ❌ Error creating lead: {e}")
            
            # Small delay to avoid overwhelming Odoo
            time.sleep(0.1)
        
        print(f"\n   📊 Page {page_id} Summary:")
        print(f"      • Found: {len(page_leads)} October leads")
        print(f"      • Created: {page_created} new leads")
        
        all_leads.extend(page_leads)
    
    # Final summary
    print(f"\n{'='*80}")
    print("🎉 OCTOBER 2025 IMPORT COMPLETE!")
    print("="*80)
    print(f"📊 Total leads found: {len(all_leads)}")
    print(f"✅ Total leads created: {total_created}")
    print(f"📄 Pages processed: {len(PAGE_IDS)}")
    
    if total_created > 0:
        print(f"\n🔗 View your leads:")
        print(f"   http://localhost:8069/web#action=217&model=crm.lead&view_type=list")
        print(f"\n💡 Campaign columns available:")
        print(f"   • Campaign (campaign name)")
        print(f"   • Source (facebook)")
        print(f"   • Medium (facebook_ads)")
        print(f"   Click the settings icon (⚙️) to enable these columns")
    
    return True

if __name__ == '__main__':
    import_october_leads()