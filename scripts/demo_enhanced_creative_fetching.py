#!/usr/bin/env python3
"""
Demonstration script for the Enhanced Meta Creative Fetching System

This script showcases the advanced high-resolution creative fetching capabilities
implemented according to Meta's official Graph API documentation.
"""

import os
import sys
import requests
from pprint import pprint

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from custom_addons.custom_crm_integration.services.meta_creative_service import MetaCreativeService


def demonstrate_enhanced_creative_fetching():
    """
    Demonstrate the enhanced creative fetching with real examples
    """
    print("=" * 80)
    print("ENHANCED META CREATIVE FETCHING SYSTEM DEMONSTRATION")
    print("=" * 80)
    print()
    
    # Get access token from environment
    access_token = os.environ.get('META_USER_ACCESS_TOKEN')
    if not access_token:
        print("❌ ERROR: META_USER_ACCESS_TOKEN not found in environment")
        print("Please set your Meta access token in the environment variables")
        return
    
    print(f"✅ Access token configured (length: {len(access_token)})")
    print()
    
    # Initialize the service
    service = MetaCreativeService(access_token)
    print("✅ MetaCreativeService initialized")
    print()
    
    # Test with different ad types if available
    test_cases = [
        {
            'name': 'Standard Image Ad',
            'ad_id': 'YOUR_STANDARD_AD_ID',  # Replace with actual ad ID
            'description': 'Tests direct creative image_url fetching'
        },
        {
            'name': 'Dynamic/Catalog Ad', 
            'ad_id': 'YOUR_DYNAMIC_AD_ID',  # Replace with actual ad ID
            'description': 'Tests asset_feed_spec and Page Post fallback strategies'
        },
        {
            'name': 'Video Ad',
            'ad_id': 'YOUR_VIDEO_AD_ID',    # Replace with actual ad ID
            'description': 'Tests video embed_html and poster extraction'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. Testing: {test_case['name']}")
        print(f"   Description: {test_case['description']}")
        print(f"   Ad ID: {test_case['ad_id']}")
        
        if test_case['ad_id'].startswith('YOUR_'):
            print("   ⚠️  SKIPPED: Replace with actual ad ID to test")
            print()
            continue
        
        try:
            # First get the creative ID from the ad
            creative_id = get_creative_id_from_ad(access_token, test_case['ad_id'])
            if not creative_id:
                print("   ❌ Could not get creative ID")
                print()
                continue
            
            print(f"   📋 Creative ID: {creative_id}")
            
            # Fetch high-resolution creative
            result = service.fetch_high_resolution_creative(test_case['ad_id'], creative_id)
            
            if result['success']:
                print("   ✅ SUCCESS!")
                print(f"   🎯 Quality: {result['quality'].upper()}")
                print(f"   🔧 Method: {result['fetch_method']}")
                print(f"   🖼️  Media URL: {result['media_url'][:60] + '...' if result['media_url'] and len(result['media_url']) > 60 else result['media_url']}")
                
                if result.get('video_embed_html'):
                    print("   🎬 Video embed HTML available")
                
                if result.get('effective_story_id'):
                    print(f"   📄 Story ID: {result['effective_story_id']}")
                
                # Show quality improvement
                if result['quality'] in ['high', 'ultra']:
                    print("   🌟 HIGH RESOLUTION ACHIEVED!")
                elif result['quality'] == 'medium':
                    print("   ⚡ Medium resolution obtained")
                else:
                    print("   📱 Low resolution (may need manual review)")
            
            else:
                print(f"   ❌ FAILED: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
        
        print()
    
    print("=" * 80)
    print("WATERFALL STRATEGY EXPLANATION")
    print("=" * 80)
    print()
    print("The system implements a 6-tier waterfall strategy based on Meta documentation:")
    print()
    print("1. 🎯 DIRECT CREATIVE: Analyzes creative.image_url for high-res indicators")
    print("   • Looks for URL patterns like '_1080x', '_large', 'original'")
    print("   • Best for: Standard single-image ads")
    print()
    print("2. 📖 OBJECT STORY SPEC: Extracts from object_story_spec")
    print("   • link_data.picture (often higher res for link ads)")  
    print("   • video_data.image_url (for video ads)")
    print("   • Best for: Link ads, video ads with custom thumbnails")
    print()
    print("3. 📄 PAGE POST FALLBACK: Uses effective_object_story_id")
    print("   • Fetches the actual Page Post created by the ad")
    print("   • Accesses full_picture field (highest res for posts)")
    print("   • Best for: All ad types, especially dynamic/catalog ads")
    print()
    print("4. 🔄 DYNAMIC ASSETS: Parses asset_feed_spec")
    print("   • Extracts individual image hashes from dynamic ads")
    print("   • Routes to AdImage endpoint for max resolution")
    print("   • Best for: Dynamic Creative, Advantage+ Catalog ads")
    print()
    print("5. 🖼️  ADIMAGE ENDPOINT: Direct access via image hash")
    print("   • Uses AdImage node for uploaded images")
    print("   • Provides original resolution URLs")
    print("   • Best for: When image_hash is available")
    print()
    print("6. 🎬 VIDEO COMPREHENSIVE: Full video handling")
    print("   • Fetches embed_html for playable videos")
    print("   • Gets high-res poster/thumbnail from Video node")
    print("   • Best for: All video ad types")
    print()
    print("Each strategy is attempted in order until high resolution is achieved!")
    print("This approach solves the 'low-res thumbnail' problem for dynamic ads.")


def get_creative_id_from_ad(access_token: str, ad_id: str) -> str:
    """Helper function to get creative ID from ad ID"""
    try:
        url = f"https://graph.facebook.com/v21.0/{ad_id}"
        params = {
            'access_token': access_token,
            'fields': 'creative{id}'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data.get('creative', {}).get('id')
    
    except Exception as e:
        print(f"Error getting creative ID: {str(e)}")
        return None


if __name__ == "__main__":
    demonstrate_enhanced_creative_fetching()