#!/usr/bin/env python3
"""
Simple test to check webhook status
"""
import requests

def check_webhook_endpoints():
    """Test different webhook endpoints"""
    
    endpoints_to_test = [
        'http://localhost:8069/webhook/meta/leads',
        'http://localhost:8069/webhook/meta/fixed',
        'http://localhost:8069/webhook/test',
    ]
    
    for url in endpoints_to_test:
        try:
            print(f'Testing {url}...')
            
            # Try GET request first
            response = requests.get(url)
            print(f'  GET Status: {response.status_code}')
            
            # If it's the test endpoint, it should work with GET
            if 'test' in url and response.status_code == 200:
                print(f'  Response: {response.text[:200]}...')
            
        except Exception as e:
            print(f'  Error: {e}')
    
    # Test if Odoo is responsive
    print('\\nTesting Odoo main page...')
    try:
        response = requests.get('http://localhost:8069/')
        print(f'Odoo Status: {response.status_code}')
    except Exception as e:
        print(f'Odoo Error: {e}')

if __name__ == '__main__':
    check_webhook_endpoints()