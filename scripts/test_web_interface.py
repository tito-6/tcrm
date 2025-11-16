#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Direct check of what fields Odoo web interface will show"""

import requests
import json

ODOO_URL = 'http://localhost:8069'
DB_NAME = 'crm'
USERNAME = 'admin'
PASSWORD = 'admin'

def login_and_check():
    """Login via web and check what's available"""
    print("🔐 Logging in via web interface...\n")
    
    session = requests.Session()
    
    # Login
    login_url = f'{ODOO_URL}/web/session/authenticate'
    login_data = {
        'jsonrpc': '2.0',
        'params': {
            'db': DB_NAME,
            'login': USERNAME,
            'password': PASSWORD
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    response = session.post(login_url, json=login_data, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    result = response.json()
    if result.get('error'):
        print(f"❌ Login error: {result['error']}")
        return
    
    print("✅ Logged in successfully\n")
    
    # Get the list view fields
    print("📊 Fetching list view configuration...")
    fields_url = f'{ODOO_URL}/web/dataset/call_kw/crm.lead/get_views'
    fields_data = {
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {
            'model': 'crm.lead',
            'method': 'get_views',
            'args': [[[False, 'list']]],
            'kwargs': {
                'options': {}
            }
        },
        'id': 1
    }
    
    response = session.post(fields_url, json=fields_data, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        return
    
    result = response.json()
    
    if result.get('error'):
        print(f"❌ Error: {result['error']}")
        return
    
    views = result.get('result', {}).get('views', {})
    list_view = views.get('list', {})
    
    # Check arch
    arch = list_view.get('arch', '')
    print(f"View arch length: {len(arch)} characters")
    
    if 'submitted_on' in arch:
        print("✅ 'submitted_on' FOUND in arch XML!")
        for i, line in enumerate(arch.split('\n')):
            if 'submitted_on' in line:
                print(f"   Line: {line.strip()}")
    else:
        print("❌ 'submitted_on' NOT in arch XML")
    
    # Check fields
    fields = list_view.get('fields', {})
    print(f"\n📋 Fields metadata count: {len(fields)}")
    
    if 'submitted_on' in fields:
        print("\n✅ 'submitted_on' FOUND in fields metadata!")
        print(f"   {json.dumps(fields['submitted_on'], indent=2)}")
    else:
        print("\n❌ 'submitted_on' NOT in fields metadata")
        print("\n   Sample of fields present:")
        for i, field_name in enumerate(list(fields.keys())[:10]):
            print(f"   - {field_name}: {fields[field_name].get('string', 'N/A')}")
    
    # Try web_search_read to see what columns would be returned
    print("\n🔍 Testing web_search_read...")
    search_url = f'{ODOO_URL}/web/dataset/call_kw/crm.lead/web_search_read'
    search_data = {
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {
            'model': 'crm.lead',
            'method': 'web_search_read',
            'args': [],
            'kwargs': {
                'domain': [],
                'fields': ['name', 'create_date', 'submitted_on'],
                'limit': 1,
                'offset': 0
            }
        },
        'id': 2
    }
    
    response = session.post(search_url, json=search_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('result') and result['result'].get('records'):
            record = result['result']['records'][0]
            print(f"   ✅ Successfully fetched record:")
            print(f"      Name: {record.get('name')}")
            print(f"      Create Date: {record.get('create_date')}")
            print(f"      Submitted On: {record.get('submitted_on')}")
        else:
            print(f"   Result: {result}")
    
if __name__ == '__main__':
    login_and_check()
