#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch leads from QUEEN VILLA page and import to Odoo"""

import sys
import os
import xmlrpc.client
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
ODOO_URL = 'http://localhost:8069'
DB_NAME = 'crm'
USERNAME = 'admin'
PASSWORD = 'admin'

# Meta Configuration
META_ACCESS_TOKEN = os.getenv('META_USER_ACCESS_TOKEN')
PAGE_ID = '542033395659747'  # QUEEN VILLA page
PAGE_NAME = 'QUEEN VILLA'

def get_page_access_token(page_id, user_token):
    """Get page access token for a specific page"""
    url = f"https://graph.facebook.com/v21.0/{page_id}"
    params = {
        'fields': 'access_token',
        'access_token': user_token
    }
    
    print(f"🔑 Getting page access token for page {page_id}...")
    response = requests.get(url, params=params)
    if response.status_code == 200:
        page_token = response.json().get('access_token')
        if page_token:
            print(f"✅ Page access token obtained\n")
            return page_token
        else:
            print(f"⚠️ No access token in response: {response.json()}\n")
            return None
    else:
        print(f"❌ Error getting page token: {response.text}\n")
        return None

def fetch_queen_villa_leads():
    """Fetch leads from QUEEN VILLA page"""
    print(f"🔍 Fetching leads from {PAGE_NAME} (Page ID: {PAGE_ID})...\n")
    
    try:
        # First, get page access token from user token
        page_token = get_page_access_token(PAGE_ID, META_ACCESS_TOKEN)
        
        if not page_token:
            print("❌ Could not get page access token")
            return []
        
        # Get leadgen forms for the page
        forms_url = f'https://graph.facebook.com/v21.0/{PAGE_ID}/leadgen_forms'
        params = {
            'access_token': page_token,
            'fields': 'id,name,status,leads_count'
        }
        
        print(f"📋 Getting forms from page {PAGE_ID}...")
        response = requests.get(forms_url, params=params)
        
        # Check response
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return []
        
        forms_data = response.json()
        
        # Check for API errors
        if 'error' in forms_data:
            print(f"❌ Meta API Error:")
            print(f"   Message: {forms_data['error'].get('message', 'Unknown error')}")
            print(f"   Type: {forms_data['error'].get('type', 'Unknown')}")
            print(f"   Code: {forms_data['error'].get('code', 'Unknown')}")
            return []
        
        if 'data' not in forms_data or not forms_data['data']:
            print(f"⚠️ No leadgen forms found for page {PAGE_ID}")
            return []
        
        print(f"✅ Found {len(forms_data['data'])} form(s)\n")
        
        all_leads = []
        
        for form in forms_data['data']:
            form_id = form['id']
            form_name = form.get('name', 'Unknown')
            leads_count = form.get('leads_count', 0)
            
            print(f"📝 Form: {form_name}")
            print(f"   ID: {form_id}")
            print(f"   Leads Count: {leads_count}")
            
            # Get ALL leads from this form with pagination
            leads_url = f'https://graph.facebook.com/v21.0/{form_id}/leads'
            leads_params = {
                'access_token': page_token,
                'fields': 'id,created_time,field_data,ad_id,adset_id,campaign_id,form_id,ad_name,adset_name,campaign_name,platform,is_organic',
                'limit': 500  # Maximum per request
            }
            
            form_leads = []
            page_count = 0
            
            while leads_url:
                page_count += 1
                leads_response = requests.get(leads_url, params=leads_params)
                leads_response.raise_for_status()
                
                leads_data = leads_response.json()
                
                if 'data' in leads_data and leads_data['data']:
                    form_leads.extend(leads_data['data'])
                    print(f"      Page {page_count}: {len(leads_data['data'])} leads")
                    
                    # Check for next page
                    if 'paging' in leads_data and 'next' in leads_data['paging']:
                        leads_url = leads_data['paging']['next']
                        leads_params = {}  # Clear params as next URL already has them
                    else:
                        leads_url = None
                else:
                    leads_url = None
            
            print(f"   ✅ Total fetched from this form: {len(form_leads)} leads\n")
            all_leads.extend(form_leads)
            
        print(f"🎉 Total leads fetched: {len(all_leads)}\n")
        return all_leads
        
    except Exception as e:
        print(f"❌ Error fetching leads: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def import_leads_to_odoo(leads):
    """Import leads into Odoo CRM"""
    if not leads:
        print("⚠️ No leads to import")
        return
    
    print(f"📥 Importing {len(leads)} leads to Odoo CRM...\n")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        
        if not uid:
            print("❌ Authentication failed")
            return
        
        print(f"✅ Authenticated as user ID: {uid}\n")
        
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        imported_count = 0
        skipped_count = 0
        
        for idx, lead_data in enumerate(leads, 1):
            try:
                meta_lead_id = lead_data.get('id')
                
                # Check if lead already exists
                existing = models.execute_kw(DB_NAME, uid, PASSWORD,
                    'crm.lead', 'search',
                    [[['description', 'ilike', f'Lead ID: {meta_lead_id}']]])
                
                if existing:
                    print(f"   ⏭️  [{idx}/{len(leads)}] Lead {meta_lead_id} already exists, skipping")
                    skipped_count += 1
                    continue
                
                # Extract and map ALL field data properly
                field_data = {}
                raw_field_data = lead_data.get('field_data', [])
                
                # Map all fields
                for item in raw_field_data:
                    field_name = item.get('name', '')
                    field_values = item.get('values', [])
                    
                    if field_values:
                        field_data[field_name] = field_values[0]
                
                # Extract name - try all possible variations
                name = ''
                for key in ['full_name', 'name', 'adı_soyadı', 'adi_soyadi', 'ad_soyad']:
                    if key in field_data:
                        name = field_data[key]
                        break
                
                if not name and 'first_name' in field_data:
                    name = field_data.get('first_name', '') + ' ' + field_data.get('last_name', '')
                    name = name.strip()
                
                # Extract email - try all possible variations
                email = ''
                for key in ['email', 'e_mail', 'e-mail', 'e-posta', 'e_posta', 'eposta']:
                    if key in field_data:
                        email = field_data[key]
                        break
                
                # Extract phone - try all possible variations and Turkish field names
                phone = ''
                for key in field_data.keys():
                    # Check for phone-related keywords
                    key_lower = key.lower()
                    if any(word in key_lower for word in ['phone', 'telefon', 'tel', 'numara', 'iletişim', 'mobile']):
                        phone = field_data[key]
                        break
                
                # If still no phone, try standard field names
                if not phone:
                    for key in ['phone_number', 'phone', 'mobile', 'mobile_number']:
                        if key in field_data:
                            phone = field_data[key]
                            break
                
                # Build detailed description with ALL fields
                description_parts = [
                    f"Lead from {PAGE_NAME}",
                    f"Lead ID: {meta_lead_id}",
                    f"Submitted On: {lead_data.get('created_time', 'Unknown')}",
                    ""
                ]
                
                # Add campaign information
                if lead_data.get('campaign_name'):
                    description_parts.append(f"Campaign: {lead_data.get('campaign_name')}")
                if lead_data.get('campaign_id'):
                    description_parts.append(f"Campaign ID: {lead_data.get('campaign_id')}")
                    
                if lead_data.get('adset_name'):
                    description_parts.append(f"Ad Set: {lead_data.get('adset_name')}")
                if lead_data.get('adset_id'):
                    description_parts.append(f"Ad Set ID: {lead_data.get('adset_id')}")
                    
                if lead_data.get('ad_name'):
                    description_parts.append(f"Ad: {lead_data.get('ad_name')}")
                if lead_data.get('ad_id'):
                    description_parts.append(f"Ad ID: {lead_data.get('ad_id')}")
                    
                if lead_data.get('form_id'):
                    description_parts.append(f"Form ID: {lead_data.get('form_id')}")
                    
                if lead_data.get('platform'):
                    description_parts.append(f"Platform: {lead_data.get('platform')}")
                    
                if lead_data.get('is_organic'):
                    description_parts.append(f"Organic: {lead_data.get('is_organic')}")
                
                if field_data:
                    description_parts.append("")
                    description_parts.append("Form Answers:")
                    for key, value in field_data.items():
                        description_parts.append(f"  • {key}: {value}")
                
                # Prepare final values
                final_name = name if name else f"Lead {meta_lead_id}"
                
                # Parse and format the submitted date
                submitted_on = lead_data.get('created_time', '')
                
                # Get campaign and platform info
                campaign_name = lead_data.get('campaign_name', '')
                adset_name = lead_data.get('adset_name', '')
                platform_raw = lead_data.get('platform', '')
                
                # Convert platform short codes to full names
                platform_mapping = {
                    'fb': 'facebook',
                    'ig': 'instagram',
                    'm': 'messenger',
                    'facebook': 'facebook',
                    'instagram': 'instagram',
                    'messenger': 'messenger'
                }
                platform = platform_mapping.get(platform_raw.lower(), False) if platform_raw else False
                
                lead_values = {
                    'name': final_name,
                    'contact_name': name if name else '',
                    'email_from': email,
                    'phone': phone,
                    'description': '\n'.join(description_parts),
                    'type': 'lead',
                    'meta_campaign_id': lead_data.get('campaign_id', ''),
                    'meta_campaign_name': campaign_name,
                    'meta_adset_id': lead_data.get('adset_id', ''),
                    'meta_adset_name': adset_name,
                    'meta_ad_id': lead_data.get('ad_id', ''),
                    'meta_ad_name': lead_data.get('ad_name', ''),
                    'meta_form_id': lead_data.get('form_id', ''),
                    'meta_platform': platform,
                }
                
                # Try to add submitted_on field if it exists in the model
                if submitted_on:
                    try:
                        # Convert ISO format to Odoo datetime format
                        from datetime import datetime
                        dt = datetime.fromisoformat(submitted_on.replace('Z', '+00:00'))
                        lead_values['submitted_on'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                # Create lead in Odoo
                lead_id = models.execute_kw(DB_NAME, uid, PASSWORD,
                    'crm.lead', 'create', [lead_values])
                
                imported_count += 1
                print(f"   ✅ [{idx}/{len(leads)}] {final_name} | {email or 'No email'} | {phone or 'No phone'}")
                
            except Exception as e:
                print(f"   ⚠️  [{idx}/{len(leads)}] Failed to import lead: {str(e)}")
        
        print(f"\n{'='*60}")
        print(f"📊 Import Summary:")
        print(f"   Total Leads: {len(leads)}")
        print(f"   Successfully Imported: {imported_count}")
        print(f"   Skipped (already exists): {skipped_count}")
        print(f"   Failed: {len(leads) - imported_count - skipped_count}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error importing leads: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main execution function"""
    print("\n" + "="*60)
    print(f"🚀 QUEEN VILLA LEADS FETCHER")
    print("="*60 + "\n")
    
    # Fetch leads from Meta
    leads = fetch_queen_villa_leads()
    
    # Import leads to Odoo
    if leads:
        import_leads_to_odoo(leads)
    
    print("✅ PROCESS COMPLETE!\n")
    print(f"🌐 View leads at: {ODOO_URL}/web#action=crm.crm_lead_all_leads")
    print(f"👤 Username: {USERNAME}")
    print(f"🔑 Password: {PASSWORD}\n")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
