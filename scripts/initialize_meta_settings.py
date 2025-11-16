#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Initialize Meta Lead Integration settings in Odoo"""

import xmlrpc.client
import os
from dotenv import load_dotenv

load_dotenv()

ODOO_URL = 'http://localhost:8069'
DB_NAME = 'crm'
USERNAME = 'admin'
PASSWORD = 'admin'

def initialize_settings():
    """Initialize Meta integration settings from .env"""
    print("🔧 Initializing Meta Lead Integration settings...\n")
    
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        
        if not uid:
            print("❌ Authentication failed")
            return
        
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        # Get token and page ID from .env
        meta_token = os.getenv('META_USER_ACCESS_TOKEN')
        page_id = '542033395659747'  # QUEEN VILLA
        
        if not meta_token:
            print("⚠️  META_USER_ACCESS_TOKEN not found in .env file")
            return
        
        # Set configuration parameters
        config_params = {
            'custom_crm_integration.meta_user_access_token': meta_token,
            'custom_crm_integration.meta_page_id': page_id,
            'custom_crm_integration.meta_auto_fetch_enabled': 'True',
            'custom_crm_integration.meta_total_leads_fetched': '110',
        }
        
        for key, value in config_params.items():
            models.execute_kw(DB_NAME, uid, PASSWORD,
                'ir.config_parameter', 'set_param',
                [key, value])
            print(f"✅ Set {key}")
        
        print("\n" + "="*60)
        print("✅ CONFIGURATION COMPLETE!")
        print("="*60)
        print("\n📍 Next steps:")
        print("   1. Go to Settings > Meta Lead Integration")
        print("   2. Verify your settings")
        print("   3. Click 'Fetch Leads Now' to test")
        print("   4. Auto-fetch runs every 2 minutes automatically!")
        print("\n" + "="*60 + "\n")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    initialize_settings()
