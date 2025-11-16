#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick database creation script"""

import requests
import time

ODOO_URL = 'http://localhost:8069'
MASTER_PASSWORD = 'admin'  # Default Odoo master password
DB_NAME = 'crm'
ADMIN_PASSWORD = 'admin'
LANG = 'en_US'
COUNTRY = 'us'

def create_database():
    """Create Odoo database"""
    print(f"🔧 Creating database '{DB_NAME}'...")
    
    try:
        url = f'{ODOO_URL}/web/database/create'
        
        data = {
            'master_pwd': MASTER_PASSWORD,
            'name': DB_NAME,
            'login': 'admin',
            'password': ADMIN_PASSWORD,
            'lang': LANG,
            'country_code': COUNTRY,
        }
        
        print("📝 Sending database creation request...")
        response = requests.post(url, json={'params': data})
        
        if response.status_code == 200:
            print(f"✅ Database '{DB_NAME}' created successfully!")
            print(f"⏳ Waiting for database initialization...")
            time.sleep(10)
            return True
        else:
            print(f"❌ Failed to create database: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == '__main__':
    create_database()
