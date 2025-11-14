#!/usr/bin/env python3
"""
Force update all leads with Ad Creative Preview content
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

def format_ad_creative_html(ad_data):
    """Format ad data into nice HTML preview"""
    
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
                <small style='color: #6c757d;'>📊 Facebook Ad Data</small>
            </div>
        </div>
        
    </div>
    """
    
    return html

def fetch_ad_basic_data(ad_id):
    """Fetch basic ad data from Facebook"""
    
    if not ad_id:
        return None
    
    try:
        # Get basic ad data
        ad_url = f"https://graph.facebook.com/v24.0/{ad_id}"
        ad_params = {
            'access_token': META_USER_ACCESS_TOKEN,
            'fields': 'id,name,status,creative{id,object_story_spec}'
        }
        
        ad_response = requests.get(ad_url, params=ad_params)
        
        if ad_response.status_code == 200:
            return ad_response.json()
        else:
            print(f"      ⚠️ Error fetching ad: {ad_response.status_code}")
            return None
            
    except Exception as e:
        print(f"      ⚠️ Error fetching ad: {e}")
        return None

def force_update_all_leads():
    """Force update all leads with meta_ad_id with ad creative data"""
    
    print("="*80)
    print("🎨 FORCE UPDATING ALL LEADS WITH AD CREATIVE PREVIEWS")
    print("📊 Fetching creative data for ALL leads with ad IDs")
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
    
    for i, lead_id in enumerate(leads_to_update, 1):
        lead = Lead.browse(lead_id)
        
        print(f"\n📧 Processing Lead {i}/{len(leads_to_update)}")
        print(f"   Name: {lead.name}")
        print(f"   Ad ID: {lead.meta_ad_id}")
        
        # Fetch ad data
        print(f"   🎨 Fetching ad data...")
        ad_data = fetch_ad_basic_data(lead.meta_ad_id)
        
        # Format the creative data as HTML
        creative_html = format_ad_creative_html(ad_data)
        
        # Update the lead
        try:
            lead.write({
                'meta_ad_creative': creative_html
            })
            
            if ad_data:
                print(f"   ✅ Updated with ad creative data")
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
    print("🎉 AD CREATIVE UPDATE COMPLETE!")
    print("="*80)
    print(f"✅ Updated {updated_count} leads total")
    print(f"🎨 {success_count} leads with actual ad creative data")
    print(f"⚠️ {updated_count - success_count} leads with 'no data' message")
    
    if updated_count > 0:
        print(f"\n🔗 View your leads with ad creatives:")
        print(f"   http://localhost:8069/web#action=217&model=crm.lead&view_type=list")
        print(f"\n💡 Ad Creative Preview now includes:")
        print(f"   🎨 Beautiful visual design with gradients")
        print(f"   📱 Ad name and detailed information")
        print(f"   💬 Ad text content formatted nicely")
        print(f"   🎯 Call-to-action buttons styled properly")
        print(f"   📊 Ad status with color coding")
        print(f"   ✨ Professional card-style layout")
        print(f"\n🎯 Open any lead card → 'Meta Lead Data' → 'Ad Creative Preview' section")
    
    return True

if __name__ == '__main__':
    force_update_all_leads()