#!/usr/bin/env python3
"""
Get a long-lived Facebook User Access Token
"""
import requests
import sys

META_APP_ID = "1576155436683126"
META_APP_SECRET = "3f5d85f87c288bd97fa1439b96875b38"

def exchange_token(short_lived_token):
    """Exchange short-lived token for long-lived token"""
    url = "https://graph.facebook.com/oauth/access_token"
    params = {
        'grant_type': 'fb_exchange_token',
        'client_id': META_APP_ID,
        'client_secret': META_APP_SECRET,
        'fb_exchange_token': short_lived_token
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get('access_token'), data.get('expires_in', 0)
    else:
        print(f"Error: {response.text}")
        return None, 0

def main():
    if len(sys.argv) != 2:
        print("Usage: python get_long_lived_token.py <short_lived_token>")
        print("\nGet short-lived token from:")
        print("https://developers.facebook.com/tools/explorer")
        print("Make sure to select your app and request these permissions:")
        print("- pages_manage_metadata")
        print("- pages_read_engagement") 
        print("- leads_retrieval")
        print("- pages_show_list")
        return
    
    short_token = sys.argv[1]
    print("Exchanging short-lived token for long-lived token...")
    
    long_token, expires_in = exchange_token(short_token)
    if long_token:
        print(f"\n✓ Success! Long-lived token (expires in {expires_in} seconds):")
        print(f"{long_token}")
        print(f"\nUpdate your .env file:")
        print(f"META_USER_ACCESS_TOKEN={long_token}")
    else:
        print("Failed to get long-lived token")

if __name__ == '__main__':
    main()