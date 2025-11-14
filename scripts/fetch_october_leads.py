#!/usr/bin/env python3
"""
Fetch all leads from October 2025 from Facebook with real campaign data
"""
import requests
import json
import odoorpc
from datetime import datetime, timezone
import time

# Facebook App Configuration
APP_ID = "1269388964449066"
APP_SECRET = "your_app_secret_here"  # You'll need to provide this
ACCESS_TOKEN = "your_access_token_here"  # You'll need to provide this

# Page ID for Model Sanayi
PAGE_ID = "61557077311249"

def get_october_leads():
    """Fetch all leads from October 2025 from Facebook"""
    
    print("="*80)
    print("FETCHING OCTOBER 2025 LEADS FROM FACEBOOK")
    print("="*80)
    
    # October 2025 date range (Unix timestamps)
    october_start = int(datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp())
    october_end = int(datetime(2025, 10, 31, 23, 59, 59, tzinfo=timezone.utc).timestamp())
    
    print(f"📅 Date Range: October 1-31, 2025")
    print(f"🔢 Unix Start: {october_start}")
    print(f"🔢 Unix End: {october_end}")
    
    # Get all lead forms for the page
    forms_url = f"https://graph.facebook.com/v20.0/{PAGE_ID}/leadgen_forms"
    forms_params = {
        'access_token': ACCESS_TOKEN,
        'fields': 'id,name,status,created_time'
    }
    
    print(f"\n📋 Fetching lead forms for page {PAGE_ID}...")
    
    try:
        forms_response = requests.get(forms_url, params=forms_params)
        forms_data = forms_response.json()
        
        if 'error' in forms_data:
            print(f"❌ Error fetching forms: {forms_data['error']['message']}")
            return []
            
        forms = forms_data.get('data', [])
        print(f"✅ Found {len(forms)} lead forms")
        
        all_leads = []
        
        for form in forms:
            form_id = form['id']
            form_name = form['name']
            
            print(f"\n📝 Processing form: {form_name} (ID: {form_id})")
            
            # Get leads for this form
            leads_url = f"https://graph.facebook.com/v20.0/{form_id}/leads"
            leads_params = {
                'access_token': ACCESS_TOKEN,
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
                'limit': 100
            }
            
            leads_response = requests.get(leads_url, params=leads_params)
            leads_data = leads_response.json()
            
            if 'error' in leads_data:
                print(f"   ❌ Error fetching leads: {leads_data['error']['message']}")
                continue
                
            form_leads = leads_data.get('data', [])
            print(f"   ✅ Found {len(form_leads)} leads for October")
            
            all_leads.extend(form_leads)
            
            # Handle pagination
            while 'paging' in leads_data and 'next' in leads_data['paging']:
                next_url = leads_data['paging']['next']
                leads_response = requests.get(next_url)
                leads_data = leads_response.json()
                
                if 'data' in leads_data:
                    form_leads = leads_data['data']
                    print(f"   📄 Fetched {len(form_leads)} more leads...")
                    all_leads.extend(form_leads)
                else:
                    break
                    
                time.sleep(0.5)  # Rate limiting
        
        print(f"\n🎯 Total October leads found: {len(all_leads)}")
        return all_leads
        
    except Exception as e:
        print(f"❌ Error fetching leads: {e}")
        return []

def fetch_campaign_data(lead):
    """Fetch campaign data for a lead"""
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
            campaign_url = f"https://graph.facebook.com/v20.0/{lead['campaign_id']}"
            campaign_params = {
                'access_token': ACCESS_TOKEN,
                'fields': 'id,name,status'
            }
            
            campaign_response = requests.get(campaign_url, params=campaign_params)
            campaign_info = campaign_response.json()
            
            if 'error' not in campaign_info:
                campaign_data['campaign_id'] = campaign_info.get('id', '')
                campaign_data['campaign_name'] = campaign_info.get('name', '')
        
        # Get ad set data if available
        if lead.get('adset_id'):
            adset_url = f"https://graph.facebook.com/v20.0/{lead['adset_id']}"
            adset_params = {
                'access_token': ACCESS_TOKEN,
                'fields': 'id,name,status'
            }
            
            adset_response = requests.get(adset_url, params=adset_params)
            adset_info = adset_response.json()
            
            if 'error' not in adset_info:
                campaign_data['adset_id'] = adset_info.get('id', '')
                campaign_data['adset_name'] = adset_info.get('name', '')
        
        # Get ad data if available
        if lead.get('ad_id'):
            ad_url = f"https://graph.facebook.com/v20.0/{lead['ad_id']}"
            ad_params = {
                'access_token': ACCESS_TOKEN,
                'fields': 'id,name,status'
            }
            
            ad_response = requests.get(ad_url, params=ad_params)
            ad_info = ad_response.json()
            
            if 'error' not in ad_info:
                campaign_data['ad_id'] = ad_info.get('id', '')
                campaign_data['ad_name'] = ad_info.get('name', '')
                
    except Exception as e:
        print(f"   ⚠️ Error fetching campaign data: {e}")
    
    return campaign_data

def process_leads_to_crm(leads):
    """Process leads and add them to CRM with campaign data"""
    
    if not leads:
        print("❌ No leads to process")
        return
    
    print(f"\n{'='*80}")
    print(f"PROCESSING {len(leads)} LEADS TO CRM")
    print("="*80)
    
    try:
        # Connect to Odoo
        print("🔗 Connecting to Odoo...")
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        print("✅ Connected to Odoo")
        
        Lead = odoo.env['crm.lead']
        
        created_count = 0
        
        for i, lead in enumerate(leads, 1):
            print(f"\n📧 Processing Lead {i}/{len(leads)}")
            print(f"   Meta ID: {lead.get('id')}")
            print(f"   Created: {lead.get('created_time')}")
            
            # Extract lead data
            field_data = lead.get('field_data', [])
            
            lead_info = {}
            for field in field_data:
                field_name = field.get('name', '').lower()
                field_value = field.get('values', [''])[0]
                
                if field_name in ['full_name', 'name']:
                    lead_info['name'] = field_value
                elif field_name in ['email']:
                    lead_info['email'] = field_value
                elif field_name in ['phone_number', 'phone']:
                    lead_info['phone'] = field_value
                elif field_name in ['city']:
                    lead_info['city'] = field_value
            
            # Get campaign data
            print(f"   🎯 Fetching campaign data...")
            campaign_data = fetch_campaign_data(lead)
            
            if campaign_data['campaign_name']:
                print(f"   ✅ Campaign: {campaign_data['campaign_name']}")
            if campaign_data['adset_name']:
                print(f"   ✅ Ad Set: {campaign_data['adset_name']}")
            if campaign_data['ad_name']:
                print(f"   ✅ Ad: {campaign_data['ad_name']}")
            
            # Create lead in CRM
            crm_lead_data = {
                'name': lead_info.get('name', 'Lead from Meta'),
                'email_from': lead_info.get('email', ''),
                'phone': lead_info.get('phone', ''),
                'city': lead_info.get('city', ''),
                'meta_leadgen_id': lead.get('id'),
                'meta_form_id': lead.get('form_id'),
                'description': f"Lead imported from Facebook on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                
                # Campaign data
                'meta_campaign_id': campaign_data['campaign_id'],
                'meta_campaign_name': campaign_data['campaign_name'],
                'meta_adset_id': campaign_data['adset_id'],
                'meta_adset_name': campaign_data['adset_name'],
                'meta_ad_id': campaign_data['ad_id'],
                'meta_ad_name': campaign_data['ad_name'],
                'meta_source': campaign_data['source'],
                'meta_medium': campaign_data['medium']
            }
            
            # Check if lead already exists
            existing_lead = Lead.search([('meta_leadgen_id', '=', lead.get('id'))])
            
            if existing_lead:
                print(f"   ⚠️ Lead already exists, skipping...")
                continue
            
            # Create new lead
            new_lead = Lead.create(crm_lead_data)
            created_count += 1
            
            print(f"   ✅ Created CRM lead ID: {new_lead}")
            
            # Small delay to avoid overwhelming the system
            time.sleep(0.1)
        
        print(f"\n{'='*80}")
        print("IMPORT COMPLETE!")
        print("="*80)
        print(f"✅ Successfully created {created_count} new leads")
        print(f"📊 Total leads processed: {len(leads)}")
        print(f"🔗 View leads: http://localhost:8069/web#action=217&model=crm.lead&view_type=list")
        
    except Exception as e:
        print(f"❌ Error processing leads to CRM: {e}")

def main():
    """Main function to fetch October leads and process them"""
    
    print("🚀 Starting October 2025 Lead Import Process")
    print("\n⚠️ IMPORTANT: You need to provide your Facebook access token!")
    print("   Update ACCESS_TOKEN variable in this script with your token")
    print("   Get it from: https://developers.facebook.com/tools/explorer/")
    
    # Check if token is configured
    if ACCESS_TOKEN == "your_access_token_here":
        print("\n❌ Please configure your Facebook access token first!")
        print("   1. Go to https://developers.facebook.com/tools/explorer/")
        print("   2. Select your app and get a token with 'leads_retrieval' permission")
        print("   3. Update ACCESS_TOKEN in this script")
        return
    
    # Fetch leads from Facebook
    leads = get_october_leads()
    
    if leads:
        # Process leads to CRM
        process_leads_to_crm(leads)
    else:
        print("❌ No leads found for October 2025")

if __name__ == '__main__':
    main()