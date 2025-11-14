#!/usr/bin/env python3
"""
Quick test to check if your Facebook access token is working
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_token(token=None):
    """Test if access token is valid and show token info"""
    
    if token:
        test_token = token
        print(f"Testing provided token: {token[:20]}...")
    else:
        test_token = os.getenv('META_USER_ACCESS_TOKEN')
        print(f"Testing token from .env: {test_token[:20] if test_token else 'None'}...")
    
    if not test_token:
        print("❌ No token provided")
        return False
    
    # Test token validity
    url = f"https://graph.facebook.com/v24.0/me?access_token={test_token}"
    response = requests.get(url)
    
    if response.status_code == 200:
        user_info = response.json()
        print("✅ Token is VALID!")
        print(f"   User: {user_info.get('name', 'Unknown')}")
        print(f"   ID: {user_info.get('id', 'Unknown')}")
        
        # Test pages access
        pages_url = f"https://graph.facebook.com/v24.0/me/accounts?access_token={test_token}"
        pages_response = requests.get(pages_url)
        
        if pages_response.status_code == 200:
            pages_data = pages_response.json()
            pages = pages_data.get('data', [])
            print(f"   Pages accessible: {len(pages)}")
            
            for page in pages[:3]:  # Show first 3 pages
                print(f"     - {page.get('name', 'Unknown')} (ID: {page.get('id', 'Unknown')})")
        
        return True
    else:
        error_data = response.json()
        print("❌ Token is INVALID!")
        print(f"   Error: {error_data.get('error', {}).get('message', 'Unknown error')}")
        return False

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # Test provided token
        test_token(sys.argv[1])
    else:
        # Test token from .env
        test_token()
        
        if not test_token():
            print("\n🔧 To get a new token:")
            print("1. Go to: https://developers.facebook.com/tools/explorer")
            print("2. Select your app: 1576155436683126")
            print("3. Generate token with permissions:")
            print("   - pages_manage_metadata")
            print("   - pages_read_engagement")
            print("   - leads_retrieval")
            print("   - pages_show_list")
            print("4. Test it: python scripts/test_token.py YOUR_NEW_TOKEN")
            print("5. Convert to long-lived: python scripts/get_long_lived_token.py YOUR_NEW_TOKEN")