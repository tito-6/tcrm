#!/usr/bin/env python3
"""
Test the enhanced Meta Creative Integration
Demonstrates real-time ad creative fetching with proper Odoo UI integration
"""
import odoorpc
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_creative_refresh():
    """Test refreshing ad creative for an existing lead"""
    
    print("🧪 TESTING ENHANCED META CREATIVE INTEGRATION")
    print("="*60)
    
    # Connect to Odoo
    try:
        print("🔗 Connecting to Odoo...")
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        print("✅ Connected successfully")
        
        Lead = odoo.env['crm.lead']
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    # Find a lead with Meta Ad ID
    leads = Lead.search([('meta_ad_id', '!=', False)], limit=1)
    
    if not leads:
        print("❌ No leads found with Meta Ad ID")
        return False
    
    lead = Lead.browse(leads[0])
    print(f"\n🎯 Testing with lead: {lead.name}")
    print(f"   Ad ID: {lead.meta_ad_id}")
    
    # Test the refresh functionality
    print("🔄 Testing ad creative refresh...")
    
    try:
        # Call the refresh method
        result = lead.action_refresh_ad_creative()
        
        # Refresh lead data
        lead = Lead.browse(lead.id)
        
        print("✅ Refresh completed!")
        print(f"   Ad Name: {lead.meta_ad_name or 'Not set'}")
        print(f"   Creative ID: {lead.meta_creative_id or 'Not set'}")
        print(f"   Creative Type: {lead.meta_creative_type or 'Not set'}")
        print(f"   Media URL: {lead.meta_creative_media_url or 'Not set'}")
        print(f"   Title: {lead.meta_creative_title or 'Not set'}")
        print(f"   CTA: {lead.meta_creative_cta or 'Not set'}")
        
        if lead.meta_creative_preview:
            print("🎨 Creative preview generated successfully!")
            preview_length = len(lead.meta_creative_preview)
            print(f"   Preview HTML size: {preview_length} characters")
        else:
            print("⚠️ No creative preview generated")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during refresh: {e}")
        return False

def test_webhook_endpoint():
    """Test if the webhook endpoint is accessible"""
    
    print("\n🌐 TESTING WEBHOOK ENDPOINTS")
    print("="*60)
    
    # Test the webhook test endpoint
    try:
        response = requests.get('http://localhost:8069/webhook/meta/test', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Webhook endpoint accessible")
            print(f"   Status: {data.get('status')}")
            print(f"   Access Token Configured: {data.get('access_token_configured')}")
            print(f"   Available Endpoints: {len(data.get('endpoints', {}))}")
            return True
        else:
            print(f"⚠️ Webhook returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        return False

def check_access_token():
    """Check if the access token is valid"""
    
    print("\n🔑 CHECKING ACCESS TOKEN")
    print("="*60)
    
    token = os.environ.get('META_USER_ACCESS_TOKEN')
    if not token:
        print("❌ No access token found in environment")
        return False
    
    # Test with a simple Graph API call
    try:
        url = "https://graph.facebook.com/v24.0/me"
        params = {'access_token': token, 'fields': 'id,name'}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Access token is valid")
            print(f"   User ID: {data.get('id')}")
            print(f"   Name: {data.get('name')}")
            return True
        else:
            print(f"❌ Token validation failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
    except Exception as e:
        print(f"❌ Token validation error: {e}")
        return False

def main():
    """Run all tests"""
    
    print("🚀 ENHANCED META CREATIVE INTEGRATION TESTS")
    print("="*80)
    
    results = []
    
    # Test 1: Access token validation
    results.append(("Access Token", check_access_token()))
    
    # Test 2: Webhook endpoints
    results.append(("Webhook Endpoint", test_webhook_endpoint()))
    
    # Test 3: Creative refresh functionality
    results.append(("Creative Refresh", test_creative_refresh()))
    
    # Summary
    print(f"\n{'='*80}")
    print("🎉 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name:<20} {status}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎊 ALL TESTS PASSED!")
        print("🔗 Ready to test in CRM: http://localhost:8069")
        print("🎯 Features available:")
        print("   ✅ Real-time webhook processing")
        print("   ✅ Automatic ad creative fetching")
        print("   ✅ Visual creative previews")
        print("   ✅ Manual refresh functionality")
        print("   ✅ Native Odoo UI integration")
    else:
        print("\n⚠️ Some tests failed. Check the logs above for details.")
    
    return passed == total

if __name__ == '__main__':
    main()