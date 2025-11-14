#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
from datetime import datetime, timedelta

def get_long_lived_token():
    """
    Generate a new long-lived access token from Meta
    
    You need to:
    1. Go to Meta for Developers: https://developers.facebook.com/apps/
    2. Select your WhatsApp Business app
    3. Go to WhatsApp > API Setup
    4. Generate a new temporary access token (valid for 1 hour)  
    5. Use that temporary token here to get a long-lived token (valid for 60 days)
    """
    
    print("🔑 WhatsApp API Token Refresh Guide")
    print("=" * 50)
    print()
    
    print("📋 Steps to get a new token:")
    print("1. Go to https://developers.facebook.com/apps/")
    print("2. Select your WhatsApp Business app")  
    print("3. Go to WhatsApp > API Setup in left menu")
    print("4. Click 'Generate access token' for a temporary token")
    print("5. Copy the temporary access token")
    print("6. Paste it below to generate a 60-day token")
    print()
    
    # Get app details from environment
    app_id = os.getenv('META_APP_ID', '1084867992850773')
    app_secret = os.getenv('META_APP_SECRET')
    
    if not app_secret:
        print("❌ META_APP_SECRET not found in environment!")
        print("📝 Add it to your .env file:")
        print("META_APP_SECRET=your_app_secret_here")
        return
    
    print(f"📱 App ID: {app_id}")
    print(f"🔐 App Secret: {'*' * 20}...{app_secret[-4:] if app_secret else 'Not Set'}")
    print()
    
    # Get temporary token from user
    temp_token = input("🔑 Paste your temporary access token here: ").strip()
    
    if not temp_token:
        print("❌ No token provided!")
        return
    
    print("\n🔄 Converting to long-lived token...")
    
    # Convert to long-lived token
    url = "https://graph.facebook.com/v21.0/oauth/access_token"
    params = {
        'grant_type': 'fb_exchange_token',
        'client_id': app_id,
        'client_secret': app_secret,
        'fb_exchange_token': temp_token
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            long_lived_token = data.get('access_token')
            expires_in = data.get('expires_in', 5184000)  # Default 60 days
            
            if long_lived_token:
                # Calculate expiry date
                expiry_date = datetime.now() + timedelta(seconds=expires_in)
                
                print("✅ Long-lived token generated successfully!")
                print(f"🕒 Expires: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')} ({expires_in//86400} days)")
                print()
                print("🔑 Your new WhatsApp access token:")
                print("=" * 50)
                print(long_lived_token)
                print("=" * 50)
                print()
                
                # Update .env file
                env_file = ".env"
                if os.path.exists(env_file):
                    print("📝 Updating .env file...")
                    
                    # Read current .env
                    with open(env_file, 'r') as f:
                        lines = f.readlines()
                    
                    # Update or add token
                    updated = False
                    new_lines = []
                    
                    for line in lines:
                        if line.startswith('WHATSAPP_ACCESS_TOKEN=') or line.startswith('META_USER_ACCESS_TOKEN='):
                            new_lines.append(f"WHATSAPP_ACCESS_TOKEN={long_lived_token}\n")
                            updated = True
                        else:
                            new_lines.append(line)
                    
                    if not updated:
                        new_lines.append(f"WHATSAPP_ACCESS_TOKEN={long_lived_token}\n")
                    
                    # Write back
                    with open(env_file, 'w') as f:
                        f.writelines(new_lines)
                    
                    print("✅ .env file updated with new token!")
                else:
                    print("⚠️ .env file not found. Please create it with:")
                    print(f"WHATSAPP_ACCESS_TOKEN={long_lived_token}")
                
                # Test the token
                print("\n🧪 Testing new token...")
                test_url = f"https://graph.facebook.com/v21.0/{os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID', '466109021426030')}"
                headers = {'Authorization': f'Bearer {long_lived_token}'}
                
                test_response = requests.get(test_url, headers=headers, timeout=30)
                
                if test_response.status_code == 200:
                    print("✅ Token test successful!")
                    print("🎉 WhatsApp API is ready to use!")
                else:
                    print(f"⚠️ Token test failed: {test_response.status_code}")
                    print(f"Response: {test_response.text}")
                    
            else:
                print("❌ No token in response")
                print(f"Response: {response.text}")
                
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    get_long_lived_token()