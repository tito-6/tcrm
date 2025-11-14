#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import requests
import json

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
    except Exception as e:
        print(f"Error reading .env file: {e}")
    return env_vars

def check_available_phone_numbers():
    """Check what phone numbers are available in your WhatsApp Business Account"""
    
    # Load environment variables from .env file
    env_vars = load_env_file()
    
    # Get configuration from environment
    access_token = env_vars.get('WHATSAPP_ACCESS_TOKEN')
    business_account_id = env_vars.get('WHATSAPP_BUSINESS_ACCOUNT_ID', '466109021426030')
    
    if not access_token:
        print("❌ WHATSAPP_ACCESS_TOKEN not found in environment!")
        return
    
    print("📱 Checking Available WhatsApp Phone Numbers")
    print("=" * 50)
    print(f"🏢 Business Account ID: {business_account_id}")
    print()
    
    # Get phone numbers from WhatsApp Business Account
    url = f"https://graph.facebook.com/v21.0/{business_account_id}/phone_numbers"
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    
    try:
        print("🔍 Fetching phone numbers from Meta API...")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            phone_numbers = data.get('data', [])
            
            if phone_numbers:
                print(f"✅ Found {len(phone_numbers)} phone number(s):")
                print()
                
                target_number = "905525242866"  # Without country code prefix
                target_found = False
                
                for i, phone in enumerate(phone_numbers, 1):
                    phone_number = phone.get('display_phone_number', 'N/A')
                    phone_id = phone.get('id', 'N/A')
                    verified_name = phone.get('verified_name', 'N/A')
                    quality_rating = phone.get('quality_rating', 'N/A')
                    status = phone.get('status', 'N/A')
                    
                    # Check if this is the target number
                    is_target = target_number in phone_number.replace('+', '').replace(' ', '')
                    if is_target:
                        target_found = True
                    
                    status_icon = "🎯" if is_target else "📞"
                    
                    print(f"{status_icon} Phone {i}:")
                    print(f"  📱 Number: {phone_number}")
                    print(f"  🆔 ID: {phone_id}")
                    print(f"  ✅ Verified Name: {verified_name}")
                    print(f"  ⭐ Quality: {quality_rating}")
                    print(f"  🟢 Status: {status}")
                    
                    if is_target:
                        print(f"  🎯 ** THIS IS YOUR TARGET NUMBER **")
                    print()
                
                if target_found:
                    print("✅ Your target number (+905525242866) is available!")
                    
                    # Find the exact phone record for the target
                    target_phone = None
                    for phone in phone_numbers:
                        if target_number in phone.get('display_phone_number', '').replace('+', '').replace(' ', ''):
                            target_phone = phone
                            break
                    
                    if target_phone:
                        new_phone_id = target_phone['id']
                        new_display_number = target_phone['display_phone_number']
                        
                        print("🔧 Configuration Update Required:")
                        print(f"   WHATSAPP_PHONE_NUMBER={target_number}")
                        print(f"   WHATSAPP_PHONE_NUMBER_ID={new_phone_id}")
                        print()
                        
                        # Update .env file
                        return update_env_file(target_number, new_phone_id)
                        
                else:
                    print("❌ Your target number (+905525242866) is NOT found in this Business Account!")
                    print("💡 You may need to:")
                    print("   1. Add the number to your WhatsApp Business Account")
                    print("   2. Verify the number is correctly registered")
                    print("   3. Check if it's in a different Business Account")
                    
            else:
                print("❌ No phone numbers found in this Business Account!")
                
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def update_env_file(phone_number, phone_number_id):
    """Update the .env file with new phone number configuration"""
    
    env_file = ".env"
    if not os.path.exists(env_file):
        print("❌ .env file not found!")
        return False
    
    try:
        print("📝 Updating .env file...")
        
        # Read current .env
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Update phone number settings
        new_lines = []
        updated_phone = False
        updated_phone_id = False
        
        for line in lines:
            if line.startswith('WHATSAPP_PHONE_NUMBER='):
                new_lines.append(f"WHATSAPP_PHONE_NUMBER={phone_number}\n")
                updated_phone = True
                print(f"  ✅ Updated WHATSAPP_PHONE_NUMBER to {phone_number}")
            elif line.startswith('WHATSAPP_PHONE_NUMBER_ID='):
                new_lines.append(f"WHATSAPP_PHONE_NUMBER_ID={phone_number_id}\n")
                updated_phone_id = True
                print(f"  ✅ Updated WHATSAPP_PHONE_NUMBER_ID to {phone_number_id}")
            else:
                new_lines.append(line)
        
        # Add if not found
        if not updated_phone:
            new_lines.append(f"WHATSAPP_PHONE_NUMBER={phone_number}\n")
            print(f"  ✅ Added WHATSAPP_PHONE_NUMBER={phone_number}")
            
        if not updated_phone_id:
            new_lines.append(f"WHATSAPP_PHONE_NUMBER_ID={phone_number_id}\n")
            print(f"  ✅ Added WHATSAPP_PHONE_NUMBER_ID={phone_number_id}")
        
        # Write back
        with open(env_file, 'w') as f:
            f.writelines(new_lines)
        
        print("✅ .env file updated successfully!")
        print()
        print("🔄 Please restart Odoo container to load the new configuration:")
        print("   docker restart odoo-web")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating .env file: {str(e)}")
        return False

if __name__ == '__main__':
    check_available_phone_numbers()