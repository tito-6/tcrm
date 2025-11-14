#!/usr/bin/env python3
"""
Update existing leads with Ad Creative Preview content
Fetches ad creative data from Facebook and formats it nicely
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

def format_ad_creative_html(ad_creative_data, ad_data):
    """Format ad creative data into nice HTML preview"""
    
    if not ad_creative_data and not ad_data:
        return "<div style='padding: 15px; background-color: #f8f9fa; border-radius: 8px;'><h4>🚫 No Ad Creative Data Available</h4><p>Ad creative information could not be retrieved.</p></div>"
    
    html_parts = []
    
    # Start container
    html_parts.append("""
    <div style='font-family: Arial, sans-serif; background-color: #ffffff; border: 1px solid #e1e5e9; border-radius: 12px; padding: 20px; margin: 10px 0;'>
        <h3 style='color: #1877f2; margin-top: 0; display: flex; align-items: center;'>
            🎨 Ad Creative Preview
        </h3>
    """)
    
    # Ad basic info
    if ad_data.get('name'):
        html_parts.append(f"""
        <div style='background-color: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 15px;'>
            <h4 style='margin: 0; color: #495057;'>📱 Ad Information</h4>
            <p style='margin: 5px 0 0 0; font-weight: bold;'>{ad_data['name']}</p>
            <small style='color: #6c757d;'>Ad ID: {ad_data.get('id', 'N/A')}</small>
        </div>
        """)
    
    # Creative content
    creative = ad_creative_data.get('creative', {}) if ad_creative_data else {}
    
    if creative:
        # Object story spec
        story_spec = creative.get('object_story_spec', {})
        
        if story_spec:
            # Page post data
            page_post_data = story_spec.get('page_post_data', {})
            
            if page_post_data:
                html_parts.append("""
                <div style='background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 15px;'>
                    <h4 style='margin: 0 0 10px 0; color: #1565c0;'>📝 Ad Content</h4>
                """)
                
                # Message/Text
                if page_post_data.get('message'):
                    message = page_post_data['message'].replace('\n', '<br>')
                    html_parts.append(f"""
                    <div style='margin-bottom: 10px;'>
                        <strong>💬 Ad Text:</strong>
                        <div style='background-color: white; padding: 10px; border-radius: 6px; margin-top: 5px; border-left: 3px solid #1877f2;'>
                            {message}
                        </div>
                    </div>
                    """)
                
                # Call to action
                if page_post_data.get('call_to_action'):
                    cta = page_post_data['call_to_action']
                    cta_type = cta.get('type', 'Unknown')
                    cta_value = cta.get('value', {})
                    
                    html_parts.append(f"""
                    <div style='margin-bottom: 10px;'>
                        <strong>🎯 Call to Action:</strong>
                        <div style='background-color: #fff3cd; padding: 8px; border-radius: 6px; margin-top: 5px;'>
                            <span style='background-color: #1877f2; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px;'>
                                {cta_type.upper()}
                            </span>
                        </div>
                    </div>
                    """)
                
                html_parts.append("</div>")
        
        # Image/Video attachments
        if creative.get('image_url'):
            html_parts.append(f"""
            <div style='background-color: #f1f3f4; padding: 15px; border-radius: 8px; margin-bottom: 15px;'>
                <h4 style='margin: 0 0 10px 0; color: #424242;'>🖼️ Creative Media</h4>
                <img src='{creative['image_url']}' style='max-width: 100%; height: auto; border-radius: 6px; border: 1px solid #ddd;' alt='Ad Creative Image'/>
            </div>
            """)
        
        # Asset details
        if creative.get('asset_feed_spec'):
            asset_spec = creative['asset_feed_spec']
            html_parts.append("""
            <div style='background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin-bottom: 15px;'>
                <h4 style='margin: 0 0 10px 0; color: #2e7d32;'>🔧 Dynamic Creative Assets</h4>
            """)
            
            # Bodies
            if asset_spec.get('bodies'):
                bodies = asset_spec['bodies']
                html_parts.append("<div style='margin-bottom: 8px;'><strong>📄 Ad Text Variations:</strong></div>")
                for i, body in enumerate(bodies[:3], 1):  # Show first 3
                    text = body.get('text', 'No text')
                    html_parts.append(f"""
                    <div style='background-color: white; padding: 8px; margin: 4px 0; border-radius: 4px; border-left: 3px solid #4caf50;'>
                        <small style='color: #666;'>Variation {i}:</small><br>
                        {text}
                    </div>
                    """)
            
            # Headlines
            if asset_spec.get('headlines'):
                headlines = asset_spec['headlines']
                html_parts.append("<div style='margin: 10px 0 8px 0;'><strong>📝 Headline Variations:</strong></div>")
                for i, headline in enumerate(headlines[:3], 1):  # Show first 3
                    text = headline.get('text', 'No headline')
                    html_parts.append(f"""
                    <div style='background-color: white; padding: 6px; margin: 3px 0; border-radius: 4px; font-weight: bold;'>
                        <small style='color: #666;'>H{i}:</small> {text}
                    </div>
                    """)
            
            # Descriptions
            if asset_spec.get('descriptions'):
                descriptions = asset_spec['descriptions']
                html_parts.append("<div style='margin: 10px 0 8px 0;'><strong>📋 Description Variations:</strong></div>")
                for i, desc in enumerate(descriptions[:2], 1):  # Show first 2
                    text = desc.get('text', 'No description')
                    html_parts.append(f"""
                    <div style='background-color: white; padding: 6px; margin: 3px 0; border-radius: 4px; font-style: italic;'>
                        <small style='color: #666;'>D{i}:</small> {text}
                    </div>
                    """)
            
            html_parts.append("</div>")
    
    # Creative status and details
    html_parts.append("""
    <div style='background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-top: 1px solid #dee2e6;'>
        <h5 style='margin: 0 0 8px 0; color: #495057;'>📊 Creative Details</h5>
    """)
    
    if ad_data.get('status'):
        status_color = "#28a745" if ad_data['status'] == 'ACTIVE' else "#ffc107"
        html_parts.append(f"""
        <p style='margin: 4px 0;'>
            <strong>Status:</strong> 
            <span style='background-color: {status_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;'>
                {ad_data['status']}
            </span>
        </p>
        """)
    
    if creative.get('id'):
        html_parts.append(f"<p style='margin: 4px 0;'><strong>Creative ID:</strong> {creative['id']}</p>")
    
    html_parts.append("</div>")
    
    # Close container
    html_parts.append("</div>")
    
    return "".join(html_parts)

def fetch_ad_creative_data(ad_id):
    """Fetch detailed ad creative data from Facebook"""
    
    if not ad_id:
        return None, None
    
    try:
        # Get ad data with creative details
        ad_url = f"https://graph.facebook.com/v24.0/{ad_id}"
        ad_params = {
            'access_token': META_USER_ACCESS_TOKEN,
            'fields': 'id,name,status,creative{id,object_story_spec,asset_feed_spec,image_url,video_id,body,title}'
        }
        
        ad_response = requests.get(ad_url, params=ad_params)
        
        if ad_response.status_code == 200:
            ad_data = ad_response.json()
            return ad_data, ad_data.get('creative')
        else:
            print(f"      ⚠️ Error fetching ad creative: {ad_response.text}")
            return None, None
            
    except Exception as e:
        print(f"      ⚠️ Error fetching ad creative: {e}")
        return None, None

def update_leads_with_ad_creatives():
    """Update existing leads with ad creative data"""
    
    print("="*80)
    print("🎨 UPDATING LEADS WITH AD CREATIVE PREVIEWS")
    print("📊 Fetching creative data for existing leads")
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
    
    # Get leads that have ad IDs but no ad creative data
    leads_to_update = Lead.search([
        ('meta_ad_id', '!=', False),
        '|',
        ('meta_ad_creative', '=', False),
        ('meta_ad_creative', '=', '')
    ])
    
    print(f"\n📊 Found {len(leads_to_update)} leads to update with ad creatives")
    
    if not leads_to_update:
        print("ℹ️ No leads found that need ad creative updates")
        return True
    
    updated_count = 0
    
    for i, lead_id in enumerate(leads_to_update, 1):
        lead = Lead.browse(lead_id)
        
        print(f"\n📧 Processing Lead {i}/{len(leads_to_update)}")
        print(f"   Name: {lead.name}")
        print(f"   Ad ID: {lead.meta_ad_id}")
        
        # Fetch ad creative data
        print(f"   🎨 Fetching ad creative data...")
        ad_data, creative_data = fetch_ad_creative_data(lead.meta_ad_id)
        
        if ad_data or creative_data:
            # Format the creative data as HTML
            creative_html = format_ad_creative_html(ad_data, ad_data)
            
            # Update the lead
            try:
                lead.write({
                    'meta_ad_creative': creative_html
                })
                
                print(f"   ✅ Updated with ad creative data")
                updated_count += 1
                
            except Exception as e:
                print(f"   ❌ Error updating lead: {e}")
        else:
            # Create a "no data" HTML
            no_data_html = format_ad_creative_html(None, None)
            
            try:
                lead.write({
                    'meta_ad_creative': no_data_html
                })
                
                print(f"   ⚠️ Updated with 'no data' message")
                updated_count += 1
                
            except Exception as e:
                print(f"   ❌ Error updating lead: {e}")
        
        # Rate limiting
        time.sleep(0.2)
    
    # Final summary
    print(f"\n{'='*80}")
    print("🎉 AD CREATIVE UPDATE COMPLETE!")
    print("="*80)
    print(f"✅ Updated {updated_count} leads with ad creative previews")
    
    if updated_count > 0:
        print(f"\n🔗 View your leads with ad creatives:")
        print(f"   http://localhost:8069/web#action=217&model=crm.lead&view_type=list")
        print(f"\n💡 Ad Creative Preview includes:")
        print(f"   🎨 Visual ad content and images")
        print(f"   📝 Ad text, headlines, and descriptions")
        print(f"   🎯 Call-to-action buttons")
        print(f"   🔧 Dynamic creative variations")
        print(f"   📊 Ad status and creative details")
        print(f"\n🎯 Open any lead card → 'Meta Lead Data' → 'Ad Creative Preview'")
    
    return True

if __name__ == '__main__':
    update_leads_with_ad_creatives()