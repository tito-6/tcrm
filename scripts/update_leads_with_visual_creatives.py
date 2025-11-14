#!/usr/bin/env python3
"""
Update leads with Ad Creative Preview including actual images and videos
Enhanced version with media preview support
"""
import odoorpc
import requests
import json
import os
from dotenv import load_dotenv
import time

load_dotenv()

# Meta credentials from .env
META_USER_ACCESS_TOKEN = os.getenv('META_USER_ACCESS_TOKEN')

def fetch_video_thumbnail(video_id):
    """Fetch video thumbnail URL from Facebook"""
    try:
        # Query the video node for thumbnails and picture
        video_url = f"https://graph.facebook.com/v24.0/{video_id}"
        video_params = {
            'access_token': META_USER_ACCESS_TOKEN,
            # request both thumbnails edge and picture field; thumbnails may require extra permissions
            'fields': 'thumbnails.limit(5){uri,height,width},picture'
        }

        response = requests.get(video_url, params=video_params)
        if response.status_code != 200:
            # print raw error to help debugging
            try:
                err = response.json()
                print(f"        ⚠️ Video thumbnail API error: {err}")
            except Exception:
                print(f"        ⚠️ Video thumbnail HTTP {response.status_code}")
            return None

        data = response.json()
        # Prefer thumbnails edge
        thumbs = data.get('thumbnails', {}).get('data', [])
        if thumbs:
            # pick the largest available thumbnail
            thumbs_sorted = sorted(thumbs, key=lambda t: (t.get('width') or 0) * (t.get('height') or 0), reverse=True)
            return thumbs_sorted[0].get('uri')

        # Fallback to picture
        return data.get('picture')
    except Exception as e:
        print(f"        ⚠️ Error fetching video thumbnail: {e}")
        return None

def format_ad_creative_html(ad_data):
    """Format ad data into nice HTML preview with actual media"""
    
    if not ad_data:
        return """
        <div style='padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; color: white; text-align: center;'>
            <h3 style='margin: 0 0 10px 0; color: white;'>🎨 Ad Creative Preview</h3>
            <p style='margin: 0; opacity: 0.9;'>⚠️ Ad creative data could not be retrieved from Facebook</p>
            <small style='opacity: 0.7;'>This may be due to permissions or the ad no longer being available</small>
        </div>
        """
    
    # Start with header
    html = f"""
    <div style='font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: white; border: 1px solid #e1e5e9; border-radius: 12px; overflow: hidden; margin: 10px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>
        
        <!-- Header -->
        <div style='background: linear-gradient(135deg, #1877f2 0%, #42a5f5 100%); padding: 20px; color: white;'>
            <h3 style='margin: 0; display: flex; align-items: center; font-size: 18px;'>
                🎨 Ad Creative Preview
                <span style='margin-left: auto; background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; font-size: 12px;'>
                    {ad_data.get('status', 'Unknown').upper()}
                </span>
            </h3>
        </div>
        
        <!-- Content -->
        <div style='padding: 20px;'>
    """
    
    # Ad basic information
    if ad_data.get('name'):
        html += f"""
        <div style='background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #1877f2;'>
            <h4 style='margin: 0 0 8px 0; color: #1877f2; font-size: 16px;'>📱 Ad Information</h4>
            <p style='margin: 0; font-size: 15px; font-weight: 600; color: #333;'>{ad_data['name']}</p>
            <p style='margin: 8px 0 0 0; font-size: 13px; color: #6c757d;'>
                <strong>Ad ID:</strong> {ad_data.get('id', 'N/A')}
            </p>
        </div>
        """
    
    # Creative content
    creative = ad_data.get('creative', {})
    
    if creative:
        html += """
        <div style='background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px;'>
            <h4 style='margin: 0 0 15px 0; color: #1565c0; font-size: 16px;'>🎯 Creative Content</h4>
        """
        
        # Media Preview Section
        media_html = ""
        
        # Check for video first
        if creative.get('video_id'):
            video_id = creative['video_id']
            print(f"        🎬 Found video ID: {video_id}")
            
            # Try to get video thumbnail
            video_thumbnail = fetch_video_thumbnail(video_id)
            
            if video_thumbnail:
                media_html += f"""
                <div style='background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; text-align: center;'>
                    <h5 style='margin: 0 0 10px 0; color: #1565c0;'>🎬 Video Creative</h5>
                    <div style='position: relative; display: inline-block;'>
                        <img src='{video_thumbnail}' style='max-width: 100%; max-height: 300px; border-radius: 8px; border: 1px solid #ddd;' alt='Video Thumbnail'/>
                        <div style='position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.7); border-radius: 50%; width: 60px; height: 60px; display: flex; align-items: center; justify-content: center;'>
                            <span style='color: white; font-size: 24px; margin-left: 4px;'>▶️</span>
                        </div>
                    </div>
                    <p style='margin: 8px 0 0 0; font-size: 12px; color: #6c757d;'>Video ID: {video_id}</p>
                </div>
                """
            else:
                media_html += f"""
                <div style='background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; text-align: center;'>
                    <h5 style='margin: 0 0 10px 0; color: #1565c0;'>🎬 Video Creative</h5>
                    <div style='background: #f8f9fa; padding: 40px; border-radius: 8px; border: 2px dashed #dee2e6;'>
                        <span style='font-size: 48px; color: #6c757d;'>🎬</span>
                        <p style='margin: 10px 0 0 0; color: #6c757d;'>Video content available</p>
                        <p style='margin: 4px 0 0 0; font-size: 12px; color: #6c757d;'>Video ID: {video_id}</p>
                    </div>
                </div>
                """
        
        # Check for image
        elif creative.get('image_url'):
            image_url = creative['image_url']
            print(f"        🖼️ Found image URL: {image_url}")
            
            media_html += f"""
            <div style='background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; text-align: center;'>
                <h5 style='margin: 0 0 10px 0; color: #1565c0;'>🖼️ Image Creative</h5>
                <img src='{image_url}' style='max-width: 100%; max-height: 300px; border-radius: 8px; border: 1px solid #ddd;' alt='Ad Creative Image'/>
            </div>
            """
        
        # Check for thumbnail_url
        elif creative.get('thumbnail_url'):
            thumbnail_url = creative['thumbnail_url']
            print(f"        🖼️ Found thumbnail URL: {thumbnail_url}")
            
            media_html += f"""
            <div style='background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; text-align: center;'>
                <h5 style='margin: 0 0 10px 0; color: #1565c0;'>🖼️ Creative Thumbnail</h5>
                <img src='{thumbnail_url}' style='max-width: 100%; max-height: 300px; border-radius: 8px; border: 1px solid #ddd;' alt='Ad Creative Thumbnail'/>
            </div>
            """
        
        # Add media HTML if we have any
        if media_html:
            html += media_html
        
        # Object story spec
        story_spec = creative.get('object_story_spec', {})
        if story_spec:
            # Page info
            page_info = story_spec.get('page_post_data', {})
            
            # Message/text content
            if page_info.get('message'):
                message = page_info['message'].replace('\n', '<br>')
                html += f"""
                <div style='background: white; padding: 15px; border-radius: 6px; margin-bottom: 12px; border-left: 3px solid #1877f2;'>
                    <strong style='color: #1877f2; font-size: 14px; display: block; margin-bottom: 8px;'>💬 Ad Text:</strong>
                    <div style='line-height: 1.5; color: #333;'>{message}</div>
                </div>
                """
            
            # Call to action
            if page_info.get('call_to_action'):
                cta = page_info['call_to_action']
                cta_type = cta.get('type', 'Unknown')
                html += f"""
                <div style='background: white; padding: 12px; border-radius: 6px; margin-bottom: 12px;'>
                    <strong style='color: #1877f2; font-size: 14px; display: block; margin-bottom: 8px;'>🎯 Call to Action:</strong>
                    <span style='background: #1877f2; color: white; padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: 600;'>
                        {cta_type.replace('_', ' ').title()}
                    </span>
                </div>
                """
        
        # Creative ID
        if creative.get('id'):
            html += f"""
            <div style='background: white; padding: 10px; border-radius: 6px; border: 1px solid #dee2e6;'>
                <small style='color: #6c757d;'>
                    <strong>Creative ID:</strong> {creative['id']}
                </small>
            </div>
            """
        
        html += "</div>"  # Close creative content div
    
    # Footer with status
    status_color = {
        'ACTIVE': '#28a745',
        'PAUSED': '#ffc107', 
        'ARCHIVED': '#6c757d',
        'DELETED': '#dc3545'
    }.get(ad_data.get('status', '').upper(), '#6c757d')
    
    html += f"""
        </div>
        
        <!-- Footer -->
        <div style='background: #f8f9fa; padding: 15px; border-top: 1px solid #dee2e6; display: flex; justify-content: space-between; align-items: center;'>
            <div>
                <small style='color: #6c757d;'>
                    <strong>Status:</strong> 
                    <span style='background: {status_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-left: 4px;'>
                        {ad_data.get('status', 'Unknown').upper()}
                    </span>
                </small>
            </div>
            <div>
                <small style='color: #6c757d;'>🎨 Visual Ad Preview</small>
            </div>
        </div>
        
    </div>
    """
    
    return html

def fetch_ad_with_media(ad_id):
    """Fetch ad data including media (images/videos)"""
    
    if not ad_id:
        return None
    
    try:
        # First get the ad and its creative id (safer for permissions and field availability)
        ad_url = f"https://graph.facebook.com/v24.0/{ad_id}"
        ad_params = {
            'access_token': META_USER_ACCESS_TOKEN,
            'fields': 'id,name,status,creative{id}'
        }

        ad_response = requests.get(ad_url, params=ad_params)
        if ad_response.status_code != 200:
            try:
                err = ad_response.json()
                print(f"      ⚠️ Error fetching ad node: {err}")
            except Exception:
                print(f"      ⚠️ Error fetching ad node: HTTP {ad_response.status_code}")
            return None

        ad_data = ad_response.json()
        creative_obj = ad_data.get('creative') or {}
        creative_id = creative_obj.get('id')

        if not creative_id:
            # no creative id, return ad data we have
            return ad_data

        # Fetch the AdCreative node directly for media fields
        creative_url = f"https://graph.facebook.com/v24.0/{creative_id}"
        creative_params = {
            'access_token': META_USER_ACCESS_TOKEN,
            # request fields that contain media info; thumbnail_url, image_url, video_id, object_story_spec
            'fields': 'id,thumbnail_url,image_url,video_id,object_story_spec,asset_feed_spec'
        }

        creative_response = requests.get(creative_url, params=creative_params)
        if creative_response.status_code != 200:
            try:
                err = creative_response.json()
                print(f"      ⚠️ Error fetching creative node: {err}")
            except Exception:
                print(f"      ⚠️ Error fetching creative node: HTTP {creative_response.status_code}")
            # attach creative id to ad_data and return
            ad_data['creative'] = {'id': creative_id}
            return ad_data

        creative_data = creative_response.json()
        # attach the detailed creative object into ad_data so formatter can use it
        ad_data['creative'] = creative_data
        return ad_data
            
    except Exception as e:
        print(f"      ⚠️ Error fetching ad: {e}")
        return None

def force_update_all_leads_with_media():
    """Force update all leads with ad creative data including media"""
    
    print("="*80)
    print("🎨 UPDATING LEADS WITH VISUAL AD CREATIVE PREVIEWS")
    print("📊 Fetching images and videos from Facebook ads")
    print("="*80)
    
    # Connect to Odoo
    try:
        print("🔗 Connecting to Odoo...")
        odoo = odoorpc.ODOO('localhost', port=8069)
        odoo.login('crm', 'admin', 'admin')
        print("✅ Connected to Odoo")
        
        Lead = odoo.env['crm.lead']
        
    except Exception as e:
        print(f"❌ Error connecting to Odoo: {e}")
        return False
    
    # Get ALL leads that have ad IDs
    leads_to_update = Lead.search([
        ('meta_ad_id', '!=', False)
    ])
    
    print(f"\n📊 Found {len(leads_to_update)} leads with ad IDs to update")
    
    if not leads_to_update:
        print("ℹ️ No leads found with ad IDs")
        return True
    
    updated_count = 0
    success_count = 0
    media_count = 0
    
    for i, lead_id in enumerate(leads_to_update, 1):
        lead = Lead.browse(lead_id)
        
        print(f"\n📧 Processing Lead {i}/{len(leads_to_update)}")
        print(f"   Name: {lead.name}")
        print(f"   Ad ID: {lead.meta_ad_id}")
        
        # Fetch ad data with media
        print(f"   🎨 Fetching ad data with media...")
        ad_data = fetch_ad_with_media(lead.meta_ad_id)
        
        # Check if we found media
        has_media = False
        if ad_data and ad_data.get('creative'):
            creative = ad_data['creative']
            if creative.get('image_url') or creative.get('video_id') or creative.get('thumbnail_url'):
                has_media = True
                media_count += 1
        
        # Format the creative data as HTML
        creative_html = format_ad_creative_html(ad_data)
        
        # Update the lead
        try:
            lead.write({
                'meta_ad_creative': creative_html
            })
            
            if ad_data:
                if has_media:
                    print(f"   ✅ Updated with ad creative and media data")
                else:
                    print(f"   ✅ Updated with ad creative data (no media)")
                success_count += 1
            else:
                print(f"   ⚠️ Updated with 'no data' message")
            
            updated_count += 1
            
        except Exception as e:
            print(f"   ❌ Error updating lead: {e}")
        
        # Rate limiting
        time.sleep(0.3)
    
    # Final summary
    print(f"\n{'='*80}")
    print("🎉 VISUAL AD CREATIVE UPDATE COMPLETE!")
    print("="*80)
    print(f"✅ Updated {updated_count} leads total")
    print(f"🎨 {success_count} leads with ad creative data")
    print(f"🖼️ {media_count} leads with visual media (images/videos)")
    print(f"⚠️ {updated_count - success_count} leads with 'no data' message")
    
    if updated_count > 0:
        print(f"\n🔗 View your leads with visual ad creatives:")
        print(f"   http://localhost:8069/web#action=217&model=crm.lead&view_type=list")
        print(f"\n💡 Visual Ad Creative Preview now includes:")
        print(f"   🎨 Beautiful visual design with gradients")
        print(f"   🖼️ Actual ad images displayed in preview")
        print(f"   🎬 Video thumbnails with play button overlay")
        print(f"   📱 Ad name and detailed information")
        print(f"   💬 Ad text content formatted nicely")
        print(f"   🎯 Call-to-action buttons styled properly")
        print(f"   📊 Ad status with color coding")
        print(f"   ✨ Professional media-rich layout")
        print(f"\n🎯 Open any lead card → 'Meta Lead Data' → 'Ad Creative Preview' section")
        print(f"🚀 You can now see the actual Facebook ad images and videos that generated each lead!")
    
    return True

if __name__ == '__main__':
    force_update_all_leads_with_media()