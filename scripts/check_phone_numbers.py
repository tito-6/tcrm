#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
from datetime import datetime

def load_env_file():
    """Load environment variables from .env file"""
    env_vars = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
                    os.environ[key] = value
    except FileNotFoundError:
        print("❌ .env file not found!")
    return env_vars

def check_available_phone_numbers():
    """Check what phone numbers are available in the WhatsApp Business Account"""
    
    print("📱 WhatsApp Phone Numbers Check")
    print("=" * 50)
    
    # Load environment
    env_vars = load_env_file()
    
    whatsapp_token = env_vars.get('WHATSAPP_ACCESS_TOKEN')
    business_account_id = env_vars.get('WHATSAPP_BUSINESS_ACCOUNT_ID')
    
    if not whatsapp_token or not business_account_id:
        print("❌ Missing token or business account ID!")
        return
    
    print(f"🏢 Business Account ID: {business_account_id}")
    print(f"🔑 Token (last 10): ...{whatsapp_token[-10:]}")
    print()
    
    # Get all phone numbers in the business account
    print("🔍 Fetching all phone numbers in Business Account...")
    try:
        url = f"https://graph.facebook.com/v21.0/{business_account_id}/phone_numbers"
        headers = {
            'Authorization': f'Bearer {whatsapp_token}',
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            phone_numbers = data.get('data', [])
            
            if phone_numbers:
                print(f"✅ Found {len(phone_numbers)} phone number(s):")
                print()
                
                for i, phone in enumerate(phone_numbers, 1):
                    print(f"📞 Phone Number {i}:")
                    print(f"   ID: {phone.get('id')}")
                    print(f"   Display Name: {phone.get('display_phone_number')}")
                    print(f"   Verified Name: {phone.get('verified_name', 'N/A')}")
                    print(f"   Status: {phone.get('name_status', 'N/A')}")
                    print(f"   Quality Rating: {phone.get('quality_rating', 'N/A')}")
                    
                    # Test if this phone number can send messages
                    phone_id = phone.get('id')
                    if phone_id:
                        print(f"   🧪 Testing message capability for {phone_id}...")
                        test_message_capability(whatsapp_token, phone_id)
                    
                    print()
            else:
                print("❌ No phone numbers found in this Business Account!")
                
        else:
            print(f"❌ Error fetching phone numbers: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def test_message_capability(token, phone_id):
    """Test if a phone number can send messages"""
    try:
        url = f"https://graph.facebook.com/v21.0/{phone_id}/messages"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Try a dry run - just check if the endpoint is accessible
        # We'll use an invalid "to" number to avoid actually sending
        payload = {
            "messaging_product": "whatsapp",
            "to": "123456789",  # Invalid number for testing
            "type": "text",
            "text": {
                "body": "Test"
            }
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 400:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', '')
            
            # If error is about invalid phone number format, that means the endpoint works
            if 'phone number' in error_msg.lower() or 'invalid' in error_msg.lower():
                print("   ✅ Send capability: Available")
            else:
                print(f"   ❌ Send capability: Error - {error_msg}")
        elif response.status_code in [200, 201]:
            print("   ✅ Send capability: Available (unexpected success)")
        else:
            print(f"   ❌ Send capability: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Send capability: Exception - {str(e)}")

if __name__ == '__main__':
    check_available_phone_numbers()