#!/usr/bin/env python3
"""
Test Script: Manual Creative Diagnostic Test
This script manually tests our Meta creative diagnostic system.
"""

import sys
import os
sys.path.append('/mnt/custom-addons')

def test_creative_diagnostic():
    """Test the creative diagnostic functionality"""
    print("🔍 TESTING META CREATIVE DIAGNOSTIC SYSTEM")
    print("=" * 60)
    
    try:
        # Import our service
        from custom_crm_integration.services.meta_creative_service import MetaCreativeService
        
        print("✅ Successfully imported MetaCreativeService")
        
        # Test API token
        service = MetaCreativeService()
        token = service._get_access_token()
        if token:
            print(f"✅ Meta access token found: {token[:20]}...")
        else:
            print("❌ No Meta access token found")
            
        # Test creative fetch with our test creative ID
        print("\n🎯 Testing creative fetch for test lead...")
        
        test_creative_id = "120210000000000789"  # From our test lead
        
        print(f"🔄 Fetching creative data for ID: {test_creative_id}")
        
        creative_data = service.fetch_high_resolution_creative(test_creative_id)
        
        if creative_data:
            print("✅ Creative data fetched successfully!")
            print(f"   📊 Method used: {creative_data.get('fetch_method', 'Unknown')}")
            print(f"   🎨 Creative Type: {creative_data.get('creative_type', 'Unknown')}")
            print(f"   🖼️  Media URL: {creative_data.get('media_url', 'None')[:50]}...")
            if creative_data.get('high_res_url'):
                print(f"   🏆 High-res URL: {creative_data['high_res_url'][:50]}...")
        else:
            print("❌ No creative data returned")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_creative_diagnostic()