#!/usr/bin/env python3
"""
Import existing leads from Facebook pages into Odoo CRM
This will fetch all historical leads from your Facebook lead generation forms
"""
import odoorpc
import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime
import time

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

def get_form_leads(form_id, page_token, limit=100):
    """Get all leads from a specific form"""
    all_leads = []
    url = f"https://graph.facebook.com/v24.0/{form_id}/leads"
    params = {
        'access_token': page_token,
        'limit': limit
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
        time.sleep(0.5)  # Rate limiting
    
    return all_leads

def get_lead_details(lead_id, page_token):
    """Get detailed lead information from Facebook"""
    url = f"https://graph.facebook.com/v24.0/{lead_id}"
    params = {
        'access_token': page_token
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting lead details for {lead_id}: {response.text}")
        return None

def create_lead_in_odoo(odoo, lead_data, page_id, form_id):
    """Create a lead in Odoo CRM from Facebook lead data"""
    Lead = odoo.env['crm.lead']
    
    # Extract field data
    field_data = lead_data.get('field_data', [])
    lead_info = {}
    
    for field in field_data:
        field_name = field.get('name', '').lower()
        field_values = field.get('values', [])
        if field_values:
            if field_name in ['email', 'email_address']:
                lead_info['email'] = field_values[0]
            elif field_name in ['phone', 'phone_number', 'mobile_phone']:
                lead_info['phone'] = field_values[0]
            elif field_name in ['first_name', 'firstname']:
                lead_info['first_name'] = field_values[0]
            elif field_name in ['last_name', 'lastname']:
                lead_info['last_name'] = field_values[0]
            elif field_name in ['full_name', 'name']:
                lead_info['full_name'] = field_values[0]
            elif field_name in ['company', 'company_name']:
                lead_info['company'] = field_values[0]
            else:
                # Store other fields in description
                lead_info[field_name] = ', '.join(field_values)
    
    # Build lead name
    if 'full_name' in lead_info:
        name = lead_info['full_name']
    elif 'first_name' in lead_info and 'last_name' in lead_info:
        name = f"{lead_info['first_name']} {lead_info['last_name']}"
    elif 'first_name' in lead_info:
        name = lead_info['first_name']
    elif 'email' in lead_info:
        name = lead_info['email']
    else:
        name = f"Lead from Facebook {lead_data.get('id', 'Unknown')}"
    
    # Build description with all field data
    description_parts = []
    for field_name, value in lead_info.items():
        if field_name not in ['first_name', 'last_name', 'full_name', 'email', 'phone', 'company']:
            description_parts.append(f"{field_name.replace('_', ' ').title()}: {value}")
    
    description = "Lead imported from Facebook\n\n" + "\n".join(description_parts) if description_parts else "Lead imported from Facebook"
    
    # Check if lead already exists
    existing_leads = Lead.search([('meta_leadgen_id', '=', lead_data.get('id'))])
    if existing_leads:
        print(f"   Lead {lead_data.get('id')} already exists, skipping...")
        return None
    
    # Create lead
    lead_vals = {
        'name': name,
        'description': description,
        'meta_leadgen_id': lead_data.get('id'),
        'meta_page_id': page_id,
        'meta_form_id': form_id,
        'meta_raw_payload': json.dumps(lead_data),
    }
    
    # Add optional fields if available
    if 'email' in lead_info:
        lead_vals['email_from'] = lead_info['email']
    if 'phone' in lead_info:
        lead_vals['phone'] = lead_info['phone']
    if 'company' in lead_info:
        lead_vals['partner_name'] = lead_info['company']
    
    try:
        lead_id = Lead.create(lead_vals)
        return lead_id
    except Exception as e:
        print(f"   Error creating lead in Odoo: {e}")
        return None

def import_leads_from_page(page_id, user_token, odoo):
    """Import all leads from a Facebook page"""
    print(f"\n{'='*60}")
    print(f"IMPORTING LEADS FROM PAGE: {page_id}")
    print('='*60)
    
    # Get page access token
    page_token = get_page_access_token(page_id, user_token)
    if not page_token:
        print(f"✗ Failed to get access token for page {page_id}")
        return 0
    
    print(f"✓ Page access token obtained")
    
    # Get lead forms
    forms = get_page_leadgen_forms(page_id, page_token)
    print(f"✓ Found {len(forms)} lead generation forms")
    
    total_imported = 0
    
    for form in forms:
        form_id = form['id']
        form_name = form['name']
        leads_count = form.get('leads_count', 0)
        
        print(f"\n📋 Processing form: {form_name}")
        print(f"   Form ID: {form_id}")
        print(f"   Total leads in form: {leads_count}")
        
        if leads_count == 0:
            print("   No leads to import")
            continue
        
        # Get all leads from this form
        print("   Fetching leads...")
        form_leads = get_form_leads(form_id, page_token)
        
        print(f"   Processing {len(form_leads)} leads...")
        imported_count = 0
        
        for i, lead_data in enumerate(form_leads, 1):
            lead_id = lead_data.get('id')
            
            # Get detailed lead data
            detailed_lead = get_lead_details(lead_id, page_token)
            if not detailed_lead:
                continue
            
            # Create lead in Odoo
            odoo_lead_id = create_lead_in_odoo(odoo, detailed_lead, page_id, form_id)
            if odoo_lead_id:
                imported_count += 1
                print(f"   ✓ Imported lead {i}/{len(form_leads)}: {lead_id}")
            else:
                print(f"   ⚠ Skipped lead {i}/{len(form_leads)}: {lead_id}")
            
            # Rate limiting
            if i % 10 == 0:
                time.sleep(1)
        
        print(f"   📊 Imported {imported_count}/{len(form_leads)} leads from {form_name}")
        total_imported += imported_count
    
    return total_imported

def main():
    print("="*70)
    print("FACEBOOK LEADS IMPORT TO ODOO CRM")
    print("="*70)
    
    # Check token
    if not META_USER_ACCESS_TOKEN:
        print("✗ META_USER_ACCESS_TOKEN not found in .env file")
        print("Please update your access token first!")
        return
    
    # Check if token is valid
    test_url = f"https://graph.facebook.com/v24.0/me?access_token={META_USER_ACCESS_TOKEN}"
    test_response = requests.get(test_url)
    if test_response.status_code != 200:
        print("✗ Invalid or expired access token!")
        print("Please get a fresh token from: https://developers.facebook.com/tools/explorer")
        print("Then run: .venv\\Scripts\\python.exe scripts\\get_long_lived_token.py YOUR_TOKEN")
        return
    
    print(f"✓ Access token is valid")
    
    # Connect to Odoo
    try:
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        print("✓ Connected to Odoo CRM")
        
        Lead = odoo.env['crm.lead']
        initial_count = len(Lead.search([]))
        print(f"✓ Current leads in CRM: {initial_count}")
        
    except Exception as e:
        print(f"✗ Failed to connect to Odoo: {e}")
        return
    
    # Import leads from all pages
    total_imported = 0
    
    for page_id in PAGE_IDS:
        imported = import_leads_from_page(page_id, META_USER_ACCESS_TOKEN, odoo)
        total_imported += imported
    
    # Final summary
    final_count = len(Lead.search([]))
    
    print(f"\n{'='*70}")
    print("IMPORT COMPLETE!")
    print('='*70)
    print(f"📊 Total leads imported: {total_imported}")
    print(f"📊 Initial CRM leads: {initial_count}")
    print(f"📊 Final CRM leads: {final_count}")
    print(f"📊 Net increase: {final_count - initial_count}")
    print("\n🎉 All existing Facebook leads have been imported to your Odoo CRM!")
    
    if total_imported > 0:
        print("\n💡 Next steps:")
        print("1. Review the imported leads in your Odoo CRM")
        print("2. Set up your webhook for real-time future leads")
        print("3. Start your lead follow-up process!")

if __name__ == '__main__':
    main()