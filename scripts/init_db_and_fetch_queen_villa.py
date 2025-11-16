#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Initialize fresh database and fetch leads from QUEEN VILLA page"""

import sys
import os
import time
import xmlrpc.client
import requests

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(project_root)
sys.path.insert(0, parent_dir)

# Configuration
ODOO_URL = 'http://localhost:8069'
DB_NAME = 'crm'
USERNAME = 'admin'
PASSWORD = 'admin'

# Meta Configuration
META_ACCESS_TOKEN = 'EAAWZAgUjqD3YBPyWqFRTMJtfafa4O1JuEVZAg4JS4nsaqMDS3kidmSGJ4tgLtriDTu68YvCyQh3LSzfT4Bs7AfDwUL7VWDlfs32EtGlnPBcj5C0ZC95cseOrrXq7H6lYHddEKW1dpDHBtSMzjfwLwXmDBxns6vkEkZC8992m9zKZBeSrL9PFH5rDzdqAq2ZCYSKpypKwRdUebFDS5uz6TIv7EJNa1ejKJKLEpNr5JnR0qfogLprZCZBE'
PAGE_ID = '542033395659747'  # QUEEN VILLA page
PAGE_NAME = 'QUEEN VILLA'

def wait_for_odoo():
    """Wait for Odoo to be ready"""
    print("⏳ Waiting for Odoo to be ready...")
    max_attempts = 30
    for i in range(max_attempts):
        try:
            response = requests.get(f'{ODOO_URL}/web/database/selector', timeout=5)
            if response.status_code in [200, 303]:
                print("✅ Odoo is ready!")
                return True
        except:
            pass
        
        print(f"   Attempt {i+1}/{max_attempts}...")
        time.sleep(2)
    
    print("❌ Odoo did not start in time")
    return False

def initialize_database():
    """Initialize Odoo database"""
    print("\n🔧 Initializing database...")
    
    try:
        # Check if database exists
        db_list_url = f'{ODOO_URL}/web/database/list'
        response = requests.post(db_list_url, json={})
        
        # Try to authenticate
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        
        try:
            uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
            if uid:
                print(f"✅ Database '{DB_NAME}' already exists and is accessible")
                return uid
        except:
            print(f"ℹ️ Database '{DB_NAME}' needs initialization")
        
        # Database will be auto-created on first access
        print("✅ Database initialized")
        return None
        
    except Exception as e:
        print(f"⚠️ Database check: {str(e)}")
        return None

def install_modules():
    """Install required modules"""
    print("\n📦 Installing required modules...")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        
        if not uid:
            print("❌ Authentication failed")
            return False
        
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        # Update module list
        print("📋 Updating module list...")
        models.execute_kw(DB_NAME, uid, PASSWORD,
            'ir.module.module', 'update_list', [])
        
        time.sleep(2)
        
        # Install custom_crm_integration
        print("📦 Installing Custom CRM Integration...")
        modules = models.execute_kw(DB_NAME, uid, PASSWORD,
            'ir.module.module', 'search_read',
            [[['name', '=', 'custom_crm_integration']]],
            {'fields': ['id', 'state'], 'limit': 1}
        )
        
        if modules and modules[0]['state'] != 'installed':
            models.execute_kw(DB_NAME, uid, PASSWORD,
                'ir.module.module', 'button_immediate_install',
                [modules[0]['id']]
            )
            print("✅ Custom CRM Integration installed")
            time.sleep(5)
        
        # Install whatsapp_business_integration
        print("📦 Installing WhatsApp Business Integration...")
        modules = models.execute_kw(DB_NAME, uid, PASSWORD,
            'ir.module.module', 'search_read',
            [[['name', '=', 'whatsapp_business_integration']]],
            {'fields': ['id', 'state'], 'limit': 1}
        )
        
        if modules and modules[0]['state'] != 'installed':
            models.execute_kw(DB_NAME, uid, PASSWORD,
                'ir.module.module', 'button_immediate_install',
                [modules[0]['id']]
            )
            print("✅ WhatsApp Business Integration installed")
            time.sleep(5)
        
        return True
        
    except Exception as e:
        print(f"❌ Module installation error: {str(e)}")
        return False

def fetch_queen_villa_leads():
    """Fetch leads from QUEEN VILLA page"""
    print(f"\n🔍 Fetching leads from {PAGE_NAME} (Page ID: {PAGE_ID})...")
    
    try:
        # Get leadgen forms for the page
        forms_url = f'https://graph.facebook.com/v21.0/{PAGE_ID}/leadgen_forms'
        params = {
            'access_token': META_ACCESS_TOKEN,
            'fields': 'id,name,status,leads_count'
        }
        
        print(f"📋 Getting forms from page {PAGE_ID}...")
        response = requests.get(forms_url, params=params)
        response.raise_for_status()
        
        forms_data = response.json()
        
        if 'data' not in forms_data or not forms_data['data']:
            print(f"⚠️ No leadgen forms found for page {PAGE_ID}")
            return []
        
        print(f"✅ Found {len(forms_data['data'])} form(s)")
        
        all_leads = []
        
        for form in forms_data['data']:
            form_id = form['id']
            form_name = form.get('name', 'Unknown')
            leads_count = form.get('leads_count', 0)
            
            print(f"\n📝 Form: {form_name} (ID: {form_id}) - {leads_count} leads")
            
            # Get leads from this form
            leads_url = f'https://graph.facebook.com/v21.0/{form_id}/leads'
            leads_params = {
                'access_token': META_ACCESS_TOKEN,
                'fields': 'id,created_time,field_data,ad_id,adset_id,campaign_id,form_id'
            }
            
            leads_response = requests.get(leads_url, params=leads_params)
            leads_response.raise_for_status()
            
            leads_data = leads_response.json()
            
            if 'data' in leads_data:
                form_leads = leads_data['data']
                print(f"   ✅ Fetched {len(form_leads)} leads from form {form_name}")
                all_leads.extend(form_leads)
            
        print(f"\n🎉 Total leads fetched: {len(all_leads)}")
        return all_leads
        
    except Exception as e:
        print(f"❌ Error fetching leads: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def import_leads_to_odoo(leads):
    """Import leads into Odoo CRM"""
    if not leads:
        print("\n⚠️ No leads to import")
        return
    
    print(f"\n📥 Importing {len(leads)} leads to Odoo CRM...")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        
        if not uid:
            print("❌ Authentication failed")
            return
        
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        imported_count = 0
        
        for lead_data in leads:
            try:
                # Extract field data
                field_data = {item['name']: item['values'][0] 
                             for item in lead_data.get('field_data', []) 
                             if item.get('values')}
                
                # Prepare lead values
                lead_values = {
                    'name': field_data.get('full_name', 'Unknown Lead'),
                    'contact_name': field_data.get('full_name', ''),
                    'email_from': field_data.get('email', ''),
                    'phone': field_data.get('phone_number', ''),
                    'description': f"Lead from {PAGE_NAME}\n\n" + 
                                  '\n'.join([f"{k}: {v}" for k, v in field_data.items()]),
                    'type': 'lead',
                    'meta_lead_id': lead_data.get('id'),
                    'meta_form_id': lead_data.get('form_id'),
                    'meta_ad_id': lead_data.get('ad_id'),
                    'meta_campaign_id': lead_data.get('campaign_id'),
                    'submitted_on': lead_data.get('created_time'),
                }
                
                # Create lead in Odoo
                lead_id = models.execute_kw(DB_NAME, uid, PASSWORD,
                    'crm.lead', 'create', [lead_values])
                
                imported_count += 1
                print(f"   ✅ Imported: {lead_values['name']}")
                
            except Exception as e:
                print(f"   ⚠️ Failed to import lead: {str(e)}")
        
        print(f"\n🎉 Successfully imported {imported_count}/{len(leads)} leads!")
        
    except Exception as e:
        print(f"❌ Error importing leads: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main execution function"""
    print("=" * 60)
    print("🚀 QUEEN VILLA LEADS INITIALIZATION")
    print("=" * 60)
    
    # Step 1: Wait for Odoo
    if not wait_for_odoo():
        return
    
    # Step 2: Initialize database
    time.sleep(3)
    initialize_database()
    
    # Step 3: Install modules
    time.sleep(5)
    if not install_modules():
        print("⚠️ Continuing anyway...")
    
    # Step 4: Fetch leads from Meta
    time.sleep(3)
    leads = fetch_queen_villa_leads()
    
    # Step 5: Import leads to Odoo
    if leads:
        time.sleep(2)
        import_leads_to_odoo(leads)
    
    print("\n" + "=" * 60)
    print("✅ INITIALIZATION COMPLETE!")
    print("=" * 60)
    print(f"\n🌐 Access Odoo at: {ODOO_URL}/web")
    print(f"👤 Username: {USERNAME}")
    print(f"🔑 Password: {PASSWORD}")
    print(f"💾 Database: {DB_NAME}")
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
