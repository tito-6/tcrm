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

def test_token_directly():
    """Test WhatsApp access token directly with Meta API"""
    
    print("🔍 Direct WhatsApp Token Test")
    print("=" * 50)
    
    # Load environment
    env_vars = load_env_file()
    
    # Get token and other details
    whatsapp_token = env_vars.get('WHATSAPP_ACCESS_TOKEN')
    phone_number_id = env_vars.get('WHATSAPP_PHONE_NUMBER_ID')
    business_account_id = env_vars.get('WHATSAPP_BUSINESS_ACCOUNT_ID')
    
    print(f"📋 Configuration:")
    print(f"  Phone Number ID: {phone_number_id}")
    print(f"  Business Account ID: {business_account_id}")
    print(f"  Token (last 10 chars): ...{whatsapp_token[-10:] if whatsapp_token else 'None'}")
    print()
    
    if not whatsapp_token:
        print("❌ No WhatsApp access token found!")
        return
    
    # Test 1: Get phone number info
    print("🧪 Test 1: Get Phone Number Information")
    try:
        url = f"https://graph.facebook.com/v21.0/{phone_number_id}"
        headers = {
            'Authorization': f'Bearer {whatsapp_token}',
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Success: {data}")
        else:
            print(f"  ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"  ❌ Exception: {str(e)}")
    
    # Test 2: Get business account info
    print("\n🧪 Test 2: Get Business Account Information")
    try:
        url = f"https://graph.facebook.com/v21.0/{business_account_id}"
        headers = {
            'Authorization': f'Bearer {whatsapp_token}',
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Success: {data}")
        else:
            print(f"  ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"  ❌ Exception: {str(e)}")
    
    # Test 3: Try to send a very simple test message
    print("\n🧪 Test 3: Test Message Send API")
    try:
        url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {whatsapp_token}',
            'Content-Type': 'application/json'
        }
        
        # Simple test message payload
        payload = {
            "messaging_product": "whatsapp",
            "to": "905525242866",  # Same number
            "type": "text",
            "text": {
                "body": "Simple test message"
            }
        }
        
        print(f"  Payload: {payload}")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"  ✅ Success: {data}")
        else:
            print(f"  ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"  ❌ Exception: {str(e)}")
    
    # Test 4: Check token permissions
    print("\n🧪 Test 4: Check Token Permissions")
    try:
        url = "https://graph.facebook.com/v21.0/me"
        headers = {
            'Authorization': f'Bearer {whatsapp_token}',
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Token info: {data}")
        else:
            print(f"  ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"  ❌ Exception: {str(e)}")

if __name__ == '__main__':
    test_token_directly()