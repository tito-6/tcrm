#!/usr/bin/env python3
"""
Import October 2025 leads with FORM ANSWERS field and limit to 20 leads for testing
Enhanced version with complete form responses display
"""
import odoorpc
import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
import time
import re

load_dotenv()

# Your Facebook page IDs
PAGE_IDS = [
    "107962304408790",   # Focus on the working page only
]

# Meta credentials from .env
META_APP_ID = os.getenv('META_APP_ID')
META_APP_SECRET = os.getenv('META_APP_SECRET')
META_USER_ACCESS_TOKEN = os.getenv('META_USER_ACCESS_TOKEN')

# Enhanced field mapping based on Meta best practices
FIELD_MAPPING = {
    'name': [
        'full_name', 'name', 'first_name', 'last_name', 
        'customer_name', 'contact_name', 'lead_name',
        'first_and_last_name', 'nome_completo', 'isim_soyisim',
        'ad_ve_soyad', 'tam_isim'
    ],
    'email': [
        'email', 'email_address', 'e_mail', 'e-mail',
        'customer_email', 'contact_email', 'work_email',
        'personal_email', 'eposta', 'email_adresi'
    ],
    'phone': [
        'phone_number', 'phone', 'mobile', 'mobile_number',
        'cell_phone', 'contact_number', 'telefon', 'telefon_numarasi',
        'cep_telefonu', 'iletisim_numarasi', 'tel', 'tel_no'
    ],
    'city': [
        'city', 'location', 'city_name', 'şehir', 'konum',
        'sehir', 'il', 'bulundugunuz_sehir'
    ],
    'company': [
        'company', 'company_name', 'business_name', 'şirket',
        'sirket', 'firma', 'firma_adi', 'sirket_adi'
    ],
    'message': [
        'message', 'comment', 'notes', 'additional_info',
        'mesaj', 'yorum', 'notlar', 'ek_bilgi'
    ]
}

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

def format_form_answers(field_data):
    """Format all form answers in a readable way"""
    
    if not field_data:
        return "No form responses available"
    
    answers = []
    answers.append("=== CLIENT FORM RESPONSES ===\n")
    
    for i, field in enumerate(field_data, 1):
        field_name = field.get('name', 'Unknown Field')
        field_values = field.get('values', [])
        field_value = field_values[0] if field_values else 'No answer'
        
        # Clean up field name for display
        display_name = field_name.replace('_', ' ').title()
        
        # Add Turkish translations for common fields
        turkish_translations = {
            'Full Name': 'Ad Soyad',
            'Email': 'E-posta',
            'Phone Number': 'Telefon Numarası',
            'City': 'Şehir',
            'Message': 'Mesaj',
            'Company': 'Şirket',
            'Ad Ve Soyad': 'Ad Soyad',
            'Eposta': 'E-posta',
            'Telefon': 'Telefon',
            'Şehir': 'Şehir',
            'Mesaj': 'Mesaj'
        }
        
        if display_name in turkish_translations:
            display_name = turkish_translations[display_name]
        
        answers.append(f"{i}. {display_name}: {field_value}")
    
    answers.append(f"\n--- Form completed with {len(field_data)} questions ---")
    
    return "\n".join(answers)

def extract_contact_info(field_data):
    """Enhanced contact extraction with multiple field name variations"""
    
    contact_info = {
        'name': '',
        'email': '',
        'phone': '',
        'city': '',
        'company': '',
        'message': ''
    }
    
    # Create a flat list of all field data for easier searching
    field_dict = {}
    for field in field_data:
        field_name = field.get('name', '').lower().strip()
        field_values = field.get('values', [])
        field_value = field_values[0] if field_values else ''
        field_dict[field_name] = field_value
    
    # Map fields using comprehensive field mapping
    for contact_type, possible_names in FIELD_MAPPING.items():
        for field_name in possible_names:
            if field_name.lower() in field_dict:
                value = field_dict[field_name.lower()].strip()
                if value and not contact_info[contact_type]:  # Only fill if empty
                    contact_info[contact_type] = value
                    break
    
    # Additional name construction logic
    if not contact_info['name']:
        first_name = ''
        last_name = ''
        
        # Look for separate first/last name fields
        for field_name, field_value in field_dict.items():
            if 'first' in field_name and 'name' in field_name:
                first_name = field_value.strip()
            elif 'last' in field_name and 'name' in field_name:
                last_name = field_value.strip()
            elif field_name in ['ad', 'isim']:
                first_name = field_value.strip()
            elif field_name in ['soyad', 'soyisim']:
                last_name = field_value.strip()
        
        if first_name or last_name:
            contact_info['name'] = f"{first_name} {last_name}".strip()
    
    # Clean and validate extracted data
    contact_info['name'] = clean_name(contact_info['name'])
    contact_info['email'] = clean_email(contact_info['email'])
    contact_info['phone'] = clean_phone(contact_info['phone'])
    
    return contact_info

def clean_name(name):
    """Clean and validate name field"""
    if not name:
        return ''
    
    # Remove extra spaces and clean
    name = re.sub(r'\s+', ' ', name.strip())
    
    # Skip if it's obviously not a real name
    skip_patterns = [
        r'^test\d*$',
        r'^dummy.*',
        r'^sample.*',
        r'example',
        r'^\d+$',  # Only numbers
        r'^[^a-zA-ZçğıöşüÇĞIÖŞÜ\s]+$'  # No letters at all
    ]
    
    for pattern in skip_patterns:
        if re.match(pattern, name, re.IGNORECASE):
            return ''
    
    return name

def clean_email(email):
    """Clean and validate email field"""
    if not email:
        return ''
    
    email = email.strip().lower()
    
    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_pattern, email):
        return email
    
    return ''

def clean_phone(phone):
    """Clean and validate phone field"""
    if not phone:
        return ''
    
    # Remove all non-digit characters except +
    phone = re.sub(r'[^\d+]', '', phone.strip())
    
    # Skip if too short or too long
    if len(phone) < 7 or len(phone) > 20:
        return ''
    
    return phone

def detect_source_platform(campaign_data, ad_data):
    """Detect if lead came from Instagram or Facebook based on campaign/ad data"""
    
    # Default to facebook
    source = 'facebook'
    
    # Check campaign name for Instagram indicators
    campaign_name = campaign_data.get('name', '').lower()
    ad_name = ad_data.get('name', '').lower()
    
    instagram_indicators = [
        'instagram', 'ig', 'insta', 'reels', 'stories',
        'feed_instagram', 'instagram_stories', 'instagram_feed'
    ]
    
    # Check if any Instagram indicators are present
    for indicator in instagram_indicators:
        if indicator in campaign_name or indicator in ad_name:
            source = 'instagram'
            break
    
    return source

def get_october_leads_for_page(page_id, page_token, limit=20):
    """Fetch October 2025 leads for a specific page with limit"""
    
    print(f"\n📄 Processing page: {page_id}")
    print(f"🔢 Limiting to first {limit} leads for testing")
    
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
        if len(all_leads) >= limit:
            break
            
        form_id = form['id']
        form_name = form['name']
        
        print(f"   📝 Processing form: {form_name}")
        
        # Calculate remaining leads needed
        remaining_limit = limit - len(all_leads)
        
        # Get leads for this form in October with enhanced fields
        leads_url = f"https://graph.facebook.com/v24.0/{form_id}/leads"
        leads_params = {
            'access_token': page_token,
            'fields': 'id,created_time,field_data,ad_id,adset_id,campaign_id,form_id,is_organic,platform',
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
            'limit': remaining_limit
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
            
        all_leads.extend(form_leads[:remaining_limit])  # Ensure we don't exceed limit
        
        time.sleep(0.3)  # Rate limiting
    
    return all_leads[:limit]  # Final safety check

def fetch_enhanced_campaign_data(lead):
    """Fetch enhanced campaign data with platform detection"""
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
    
    ad_details = {}
    campaign_details = {}
    
    try:
        # Get campaign data
        if lead.get('campaign_id'):
            campaign_url = f"https://graph.facebook.com/v24.0/{lead['campaign_id']}"
            campaign_params = {
                'access_token': META_USER_ACCESS_TOKEN,
                'fields': 'id,name,status,objective'
            }
            
            campaign_response = requests.get(campaign_url, params=campaign_params)
            
            if campaign_response.status_code == 200:
                campaign_details = campaign_response.json()
                campaign_data['campaign_id'] = campaign_details.get('id', '')
                campaign_data['campaign_name'] = campaign_details.get('name', '')
        
        # Get ad set data
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
        
        # Get ad data with enhanced details
        if lead.get('ad_id'):
            ad_url = f"https://graph.facebook.com/v24.0/{lead['ad_id']}"
            ad_params = {
                'access_token': META_USER_ACCESS_TOKEN,
                'fields': 'id,name,status'
            }
            
            ad_response = requests.get(ad_url, params=ad_params)
            
            if ad_response.status_code == 200:
                ad_details = ad_response.json()
                campaign_data['ad_id'] = ad_details.get('id', '')
                campaign_data['ad_name'] = ad_details.get('name', '')
        
        # Detect source platform (Instagram vs Facebook)
        detected_source = detect_source_platform(campaign_details, ad_details)
        campaign_data['source'] = detected_source
        
        # Adjust medium based on platform
        if detected_source == 'instagram':
            campaign_data['medium'] = 'instagram_ads'
        else:
            campaign_data['medium'] = 'facebook_ads'
        
        # Small delay to respect rate limits
        time.sleep(0.1)
                
    except Exception as e:
        print(f"      ⚠️ Error fetching enhanced campaign data: {e}")
    
    return campaign_data

def import_october_leads_with_form_answers():
    """Import 20 October leads with Form Answers field"""
    
    print("="*80)
    print("🚀 IMPORTING 20 OCTOBER LEADS WITH FORM ANSWERS")
    print("📋 Testing new Form Answers field")
    print("="*80)
    
    # Verify credentials
    if not META_USER_ACCESS_TOKEN:
        print("❌ META_USER_ACCESS_TOKEN not found in .env file")
        return False
    
    print(f"📅 Target Period: October 1-31, 2025")
    print(f"🔢 Limit: 20 leads for testing")
    print(f"📄 Page to process: {PAGE_IDS[0]}")
    
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
    
    # Process the page
    page_id = PAGE_IDS[0]
    
    print(f"\n{'='*60}")
    print(f"PROCESSING PAGE: {page_id}")
    print('='*60)
    
    # Get page access token
    page_token = get_page_access_token(page_id, META_USER_ACCESS_TOKEN)
    
    if not page_token:
        print(f"❌ Could not get page token for {page_id}")
        return False
    
    # Get 20 October leads for this page
    page_leads = get_october_leads_for_page(page_id, page_token, limit=20)
    
    if not page_leads:
        print(f"   ℹ️ No October leads found for page {page_id}")
        return False
    
    print(f"\n📊 Processing {len(page_leads)} leads from page {page_id}")
    
    created_count = 0
    instagram_count = 0
    facebook_count = 0
    
    for i, lead in enumerate(page_leads, 1):
        print(f"\n   📧 Lead {i}/{len(page_leads)}")
        print(f"      Meta ID: {lead.get('id')}")
        print(f"      Created: {lead.get('created_time')}")
        print(f"      Form: {lead.get('form_name', 'Unknown')}")
        
        # Enhanced contact extraction
        field_data = lead.get('field_data', [])
        contact_info = extract_contact_info(field_data)
        
        # Format form answers
        form_answers = format_form_answers(field_data)
        
        # Skip leads with no meaningful contact information
        if not contact_info['name'] and not contact_info['email']:
            print(f"      ⚠️ No contact info found, skipping lead...")
            continue
        
        # Fetch enhanced campaign data with platform detection
        print(f"      🎯 Fetching enhanced campaign data...")
        campaign_data = fetch_enhanced_campaign_data(lead)
        
        # Track platform statistics
        if campaign_data['source'] == 'instagram':
            instagram_count += 1
            print(f"      📱 Platform: Instagram")
        else:
            facebook_count += 1
            print(f"      📘 Platform: Facebook")
        
        if campaign_data['campaign_name']:
            print(f"      ✅ Campaign: {campaign_data['campaign_name']}")
        
        # Generate meaningful lead name
        lead_name = contact_info['name'] or f"Lead from {campaign_data['source'].title()}"
        if not contact_info['name'] and contact_info['email']:
            lead_name = f"Email Lead - {contact_info['email'].split('@')[0]}"
        
        # Create enhanced lead description
        description_parts = [f"October 2025 lead from {campaign_data['source'].title()}"]
        if lead.get('form_name'):
            description_parts.append(f"Form: {lead.get('form_name')}")
        if contact_info['message']:
            description_parts.append(f"Message: {contact_info['message']}")
        
        description = " | ".join(description_parts)
        
        print(f"      📝 Form Answers: {len(field_data)} questions captured")
        
        # Create lead in Odoo CRM with enhanced data + form answers
        crm_lead_data = {
            'name': lead_name,
            'email_from': contact_info['email'],
            'phone': contact_info['phone'],
            'city': contact_info['city'],
            'partner_name': contact_info['company'],
            'description': description,
            'meta_leadgen_id': lead.get('id'),
            'meta_form_id': lead.get('form_id'),
            
            # NEW: Form Answers field
            'meta_form_answers': form_answers,
            
            # Enhanced campaign tracking data
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
            print(f"      👤 Name: {lead_name}")
            print(f"      📧 Email: {contact_info['email'] or 'N/A'}")
            print(f"      📱 Phone: {contact_info['phone'] or 'N/A'}")
            
            created_count += 1
            
        except Exception as e:
            print(f"      ❌ Error creating lead: {e}")
        
        # Small delay to avoid overwhelming Odoo
        time.sleep(0.1)
    
    # Final summary
    print(f"\n{'='*80}")
    print("🎉 FORM ANSWERS TEST IMPORT COMPLETE!")
    print("="*80)
    print(f"✅ Total leads created: {created_count}")
    print(f"📘 Facebook leads: {facebook_count}")
    print(f"📱 Instagram leads: {instagram_count}")
    
    if created_count > 0:
        print(f"\n🔗 View your leads with Form Answers:")
        print(f"   http://localhost:8069/web#action=217&model=crm.lead&view_type=list")
        print(f"\n💡 New Form Answers field shows:")
        print(f"   📝 All client's original form responses")
        print(f"   🗣️ Question names and answers formatted nicely")
        print(f"   🌍 Turkish and English field translations")
        print(f"   📊 Complete form completion summary")
        print(f"\n🎯 Open any lead card to see the 'Form Answers' field!")
    
    return True

if __name__ == '__main__':
    import_october_leads_with_form_answers()