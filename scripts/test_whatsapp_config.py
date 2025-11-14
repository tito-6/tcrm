#!/usr/bin/env python3
"""
WhatsApp Business API Configuration Test Script
Run this to verify your WhatsApp setup is working
"""

import os
import sys
import requests
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_whatsapp_config():
    """Test WhatsApp Business API configuration"""
    print("🔍 Testing WhatsApp Business API Configuration...")
    print("=" * 50)
    
    # Check environment variables
    access_token = os.getenv('WHATSAPP_ACCESS_TOKEN') or os.getenv('META_USER_ACCESS_TOKEN')
    phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    business_account_id = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID')
    
    print(f"✓ Access Token: {'Found' if access_token else '❌ Missing'}")
    print(f"✓ Phone Number ID: {'Found' if phone_number_id else '❌ Missing'}")
    print(f"✓ Business Account ID: {'Found' if business_account_id else '❌ Missing'}")
    
    if not access_token:
        print("\n❌ WHATSAPP_ACCESS_TOKEN is required")
        return False
    
    if not phone_number_id:
        print("\n⚠️  WHATSAPP_PHONE_NUMBER_ID is missing")
        print("   Get this from: Meta for Developers → Your App → WhatsApp → API Setup")
        return False
    
    # Test API connection
    print(f"\n🔗 Testing API Connection...")
    try:
        url = f"https://graph.facebook.com/v21.0/{phone_number_id}"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Connection: SUCCESS")
            print(f"   Phone Number: {data.get('display_phone_number', 'N/A')}")
            print(f"   Verified Name: {data.get('verified_name', 'N/A')}")
            return True
        else:
            print(f"❌ API Connection: FAILED ({response.status_code})")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API Connection: ERROR - {str(e)}")
        return False

def test_phone_validation():
    """Test phone number validation"""
    print(f"\n📱 Testing Phone Number Validation...")
    
    try:
        import phonenumbers
        from phonenumbers import NumberParseException
        
        # Test phone numbers
        test_numbers = [
            "+1234567890",
            "1234567890", 
            "+55 11 99999-9999",
            "invalid"
        ]
        
        for number in test_numbers:
            try:
                parsed = phonenumbers.parse(number, None)
                is_valid = phonenumbers.is_valid_number(parsed)
                formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                formatted = formatted.lstrip('+')
                
                print(f"   {number} → {'✅' if is_valid else '❌'} {formatted if is_valid else 'Invalid'}")
                
            except NumberParseException:
                print(f"   {number} → ❌ Parse Error")
        
        return True
        
    except ImportError:
        print("❌ phonenumbers library not installed")
        print("   Install: pip install phonenumbers")
        return False

if __name__ == "__main__":
    print("🚀 WhatsApp Business API Configuration Test")
    print("=" * 50)
    
    config_ok = test_whatsapp_config()
    phone_ok = test_phone_validation()
    
    print("\n" + "=" * 50)
    if config_ok and phone_ok:
        print("🎉 WhatsApp configuration is ready!")
        print("   You can now install and test the WhatsApp integration module.")
    else:
        print("⚠️  Configuration needs attention.")
        print("   Please fix the issues above before proceeding.")