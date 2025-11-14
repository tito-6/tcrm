#!/usr/bin/env python3

"""
WhatsApp Business API Configuration Test and Setup
This script tests your WhatsApp Business API setup and gets the phone number ID.
"""

import requests
import json
import os
from pathlib import Path

def test_whatsapp_setup():
    """Test WhatsApp Business API setup and get phone number ID"""
    
    # Load from .env file manually
    env_path = Path(".env")
    env_vars = {}
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    
    access_token = env_vars.get('WHATSAPP_ACCESS_TOKEN') or env_vars.get('META_USER_ACCESS_TOKEN')
    business_account_id = env_vars.get('WHATSAPP_BUSINESS_ACCOUNT_ID', '208940203462006')
    phone_number = env_vars.get('WHATSAPP_PHONE_NUMBER', '905525242866')
    
    print("=" * 60)
    print("🔍 WhatsApp Business API Configuration Test")
    print("=" * 60)
    
    print(f"📱 Phone Number: +{phone_number}")
    print(f"🏢 Business Account ID: {business_account_id}")
    print(f"🔑 Access Token: {access_token[:20] + '...' if access_token else 'NOT FOUND'}")
    print()
    
    if not access_token:
        print("❌ No access token found!")
        return False
    
    # Test 1: Verify Business Account
    print("🔍 Step 1: Testing Business Account Access...")
    try:
        url = f"https://graph.facebook.com/v21.0/{business_account_id}"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Business Account accessible")
            print(f"   Name: {data.get('name', 'N/A')}")
            print(f"   ID: {data.get('id', 'N/A')}")
        else:
            print(f"❌ Business Account access failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error accessing business account: {str(e)}")
        return False
    
    print()
    
    # Test 2: Get Phone Numbers from WhatsApp Business Account
    print("📱 Step 2: Getting WhatsApp Phone Numbers...")
    try:
        # Get phone numbers from the WhatsApp Business Account
        url = f"https://graph.facebook.com/v21.0/{business_account_id}/phone_numbers"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            phone_numbers = data.get('data', [])
            
            if phone_numbers:
                print("✅ Phone numbers found:")
                
                phone_number_id = None
                for phone in phone_numbers:
                    display_number = phone.get('display_phone_number', '')
                    phone_id = phone.get('id', '')
                    status = phone.get('status', '')
                    quality = phone.get('quality_rating', 'N/A')
                    
                    print(f"   📞 {display_number}")
                    print(f"      ID: {phone_id}")
                    print(f"      Status: {status}")
                    print(f"      Quality: {quality}")
                    
                    # Check if this matches our configured number
                    clean_display = display_number.replace('+', '').replace(' ', '').replace('-', '')
                    clean_config = phone_number.replace('+', '').replace(' ', '').replace('-', '')
                    
                    if clean_config in clean_display or clean_display in clean_config:
                        print(f"      ✅ THIS IS YOUR CONFIGURED NUMBER!")
                        phone_number_id = phone_id
                    print()
                
                # Update .env file with phone number ID
                if phone_number_id:
                    update_env_file(phone_number_id)
                    return True
                else:
                    print("❌ Your configured phone number was not found in the WhatsApp Business Account")
                    print(f"   Looking for: +{phone_number}")
                    return False
                    
            else:
                print("❌ No phone numbers found in this Business Account")
                return False
                
        else:
            print(f"❌ Failed to get phone numbers: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error getting phone numbers: {str(e)}")
        return False

def update_env_file(phone_number_id, waba_id=None):
    """Update .env file with the phone number ID and WABA ID"""
    try:
        env_path = Path(".env")
        
        # Read current content
        with open(env_path, 'r') as f:
            content = f.read()
        
        # Update phone number ID
        if 'WHATSAPP_PHONE_NUMBER_ID=' in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('WHATSAPP_PHONE_NUMBER_ID='):
                    lines[i] = f'WHATSAPP_PHONE_NUMBER_ID={phone_number_id}'
                    break
            content = '\n'.join(lines)
        else:
            if not content.endswith('\n'):
                content += '\n'
            content += f'WHATSAPP_PHONE_NUMBER_ID={phone_number_id}\n'
        
        # Update WABA ID if provided
        if waba_id:
            if 'WHATSAPP_BUSINESS_ACCOUNT_ID=' in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith('WHATSAPP_BUSINESS_ACCOUNT_ID='):
                        lines[i] = f'WHATSAPP_BUSINESS_ACCOUNT_ID={waba_id}'
                        break
                content = '\n'.join(lines)
            else:
                if not content.endswith('\n'):
                    content += '\n'
                content += f'WHATSAPP_BUSINESS_ACCOUNT_ID={waba_id}\n'
        
        # Write back to file
        with open(env_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated .env file:")
        print(f"   WHATSAPP_PHONE_NUMBER_ID={phone_number_id}")
        if waba_id:
            print(f"   WHATSAPP_BUSINESS_ACCOUNT_ID={waba_id}")
        
    except Exception as e:
        print(f"❌ Error updating .env file: {str(e)}")

def test_message_templates(access_token, business_account_id):
    """Test getting message templates"""
    print("📋 Step 3: Checking Message Templates...")
    try:
        url = f"https://graph.facebook.com/v21.0/{business_account_id}/message_templates"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            templates = data.get('data', [])
            
            if templates:
                print(f"✅ Found {len(templates)} message templates:")
                for template in templates[:3]:  # Show first 3
                    print(f"   📄 {template.get('name', 'N/A')}")
                    print(f"      Language: {template.get('language', 'N/A')}")
                    print(f"      Status: {template.get('status', 'N/A')}")
                    print()
                
                if len(templates) > 3:
                    print(f"   ... and {len(templates) - 3} more templates")
                    
            else:
                print("⚠️  No message templates found")
                print("   You may need to create templates in Meta Business Manager")
                
        else:
            print(f"⚠️  Could not fetch templates: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️  Error getting templates: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting WhatsApp Business API Setup...")
    
    if test_whatsapp_setup():
        print("=" * 60)
        print("🎉 WhatsApp Configuration Successful!")
        print("=" * 60)
        print("✅ Your WhatsApp Business integration is ready!")
        print("✅ Phone Number ID has been added to .env file")
        print("✅ You can now install the WhatsApp module in Odoo")
        print()
        print("Next steps:")
        print("1. Restart Odoo container: docker-compose restart odoo")
        print("2. Install the WhatsApp Business Integration module")
        print("3. Test sending messages through the Odoo interface")
    else:
        print("=" * 60)
        print("❌ Configuration Failed")
        print("=" * 60)
        print("Please check the errors above and fix them before proceeding.")