#!/usr/bin/env python3
"""
Check lead data and fix creative preview issues
"""
import odoorpc
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def check_lead_data():
    """Check current lead data"""
    
    # Connect to Odoo
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    Lead = odoo.env['crm.lead']
    
    # Get lead
    leads = Lead.search([('name', '=', 'Hasan Durak')], limit=1)
    if leads:
        lead = Lead.browse(leads[0])
        print('Current Lead Data:')
        print(f'  Name: {lead.name}')
        print(f'  Ad ID: {lead.meta_ad_id}')
        print(f'  Ad Name: {lead.meta_ad_name}')
        print(f'  Creative ID: {lead.meta_creative_id}')
        print(f'  Creative Type: {lead.meta_creative_type}')
        print(f'  Media URL: {lead.meta_creative_media_url}')
        print(f'  Body: {lead.meta_creative_body}')
        print(f'  Title: {lead.meta_creative_title}')
        print(f'  CTA: {lead.meta_creative_cta}')
        print(f'  Preview: {len(lead.meta_creative_preview or "")} chars')
        
        # Try to fetch fresh data
        print("\nFetching fresh creative data...")
        token = os.environ.get('META_USER_ACCESS_TOKEN')
        if token and lead.meta_ad_id:
            try:
                # Get ad data
                ad_url = f"https://graph.facebook.com/v24.0/{lead.meta_ad_id}"
                ad_params = {
                    'access_token': token,
                    'fields': 'id,name,status,creative{id,object_story_spec,image_url,video_id,thumbnail_url}'
                }
                
                response = requests.get(ad_url, params=ad_params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Fresh ad data: {data}")
                    
                    creative = data.get('creative', {})
                    if creative.get('id'):
                        # Get creative details
                        creative_url = f"https://graph.facebook.com/v24.0/{creative['id']}"
                        creative_params = {
                            'access_token': token,
                            'fields': 'id,name,object_story_spec,image_url,video_id,thumbnail_url,body,title'
                        }
                        
                        creative_response = requests.get(creative_url, params=creative_params, timeout=10)
                        if creative_response.status_code == 200:
                            creative_data = creative_response.json()
                            print(f"✅ Fresh creative data: {creative_data}")
                        else:
                            print(f"❌ Creative fetch error: {creative_response.text}")
                else:
                    print(f"❌ Ad fetch error: {response.text}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == '__main__':
    check_lead_data()