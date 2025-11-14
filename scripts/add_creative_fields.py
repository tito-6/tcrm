#!/usr/bin/env python3
"""
Add creative fields directly to CRM lead and update existing data
"""
import odoorpc
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def add_creative_fields():
    """Add creative fields directly to crm.lead model"""
    
    # Connect to Odoo
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    
    # Get field model
    FieldModel = odoo.env['ir.model.fields']
    Model = odoo.env['ir.model']
    
    # Get crm.lead model
    lead_model = Model.search([('model', '=', 'crm.lead')], limit=1)
    if not lead_model:
        print('❌ CRM Lead model not found')
        return
    
    model_id = lead_model[0]
    
    # Define creative fields to add
    creative_fields = [
        {
            'name': 'meta_creative_id',
            'field_description': 'Meta Creative ID',
            'ttype': 'char',
            'readonly': True,
        },
        {
            'name': 'meta_creative_type',
            'field_description': 'Meta Creative Type',
            'ttype': 'char',
            'readonly': True,
        },
        {
            'name': 'meta_creative_media_url',
            'field_description': 'Meta Creative Media URL',
            'ttype': 'char',
            'readonly': True,
        },
        {
            'name': 'meta_creative_body',
            'field_description': 'Meta Creative Body',
            'ttype': 'text',
            'readonly': True,
        },
        {
            'name': 'meta_creative_title',
            'field_description': 'Meta Creative Title',
            'ttype': 'char',
            'readonly': True,
        },
        {
            'name': 'meta_creative_cta',
            'field_description': 'Meta Creative CTA',
            'ttype': 'char',
            'readonly': True,
        },
    ]
    
    # Add fields
    for field_def in creative_fields:
        # Check if field already exists
        existing = FieldModel.search([
            ('model', '=', 'crm.lead'),
            ('name', '=', field_def['name'])
        ])
        
        if existing:
            print(f'✅ Field {field_def["name"]} already exists')
        else:
            try:
                field_def['model_id'] = model_id
                field_def['model'] = 'crm.lead'
                field_def['state'] = 'manual'
                
                field_id = FieldModel.create(field_def)
                print(f'✅ Created field {field_def["name"]} with ID {field_id}')
            except Exception as e:
                print(f'❌ Error creating field {field_def["name"]}: {e}')

def update_lead_creative_data():
    """Update existing lead with creative data"""
    
    # Connect to Odoo
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    
    Lead = odoo.env['crm.lead']
    
    # Find the test lead
    leads = Lead.search([('name', '=', 'Hasan Durak')], limit=1)
    if not leads:
        print('❌ Test lead not found')
        return
    
    lead = Lead.browse(leads[0])
    print(f'Found lead: {lead.name}')
    
    # Get access token
    access_token = os.environ.get('META_USER_ACCESS_TOKEN')
    if not access_token:
        print('❌ Meta access token not found')
        return
    
    # Get ad ID from description or set manually
    ad_id = '120232150679000652'  # Use the ad ID we found earlier
    
    try:
        # Fetch ad creative data
        ad_url = f"https://graph.facebook.com/v24.0/{ad_id}"
        ad_params = {
            'access_token': access_token,
            'fields': 'id,name,status,creative{id,object_story_spec,image_url,video_id,thumbnail_url}'
        }
        
        response = requests.get(ad_url, params=ad_params, timeout=10)
        if response.status_code == 200:
            ad_data = response.json()
            creative = ad_data.get('creative', {})
            
            if creative.get('id'):
                # Get detailed creative data
                creative_url = f"https://graph.facebook.com/v24.0/{creative['id']}"
                creative_params = {
                    'access_token': access_token,
                    'fields': 'id,name,object_story_spec,image_url,video_id,thumbnail_url,body,title'
                }
                
                creative_response = requests.get(creative_url, params=creative_params, timeout=10)
                if creative_response.status_code == 200:
                    creative_data = creative_response.json()
                    
                    # Prepare update data
                    update_data = {}
                    
                    # Check if fields exist before updating
                    try:
                        # Try to access the field to see if it exists
                        if hasattr(lead, 'meta_creative_id'):
                            update_data['meta_creative_id'] = creative_data.get('id')
                            
                        if hasattr(lead, 'meta_creative_media_url'):
                            media_url = creative_data.get('image_url') or creative_data.get('thumbnail_url')
                            update_data['meta_creative_media_url'] = media_url
                            
                        if hasattr(lead, 'meta_creative_body'):
                            update_data['meta_creative_body'] = creative_data.get('body')
                            
                        if hasattr(lead, 'meta_creative_title'):
                            update_data['meta_creative_title'] = creative_data.get('title')
                            
                        if hasattr(lead, 'meta_creative_type'):
                            creative_type = 'video' if creative_data.get('video_id') else 'image'
                            update_data['meta_creative_type'] = creative_type
                            
                        if hasattr(lead, 'meta_creative_cta'):
                            object_story = creative_data.get('object_story_spec', {})
                            cta = None
                            if 'link_data' in object_story:
                                cta = object_story['link_data'].get('call_to_action', {}).get('type')
                            update_data['meta_creative_cta'] = cta
                    
                    except Exception as e:
                        print(f'Error checking fields: {e}')
                    
                    if update_data:
                        try:
                            lead.write(update_data)
                            print(f'✅ Updated lead with creative data: {update_data}')
                        except Exception as e:
                            print(f'❌ Error updating lead: {e}')
                    else:
                        print('❌ No creative fields available to update')
                        
                        # Try to add the fields manually
                        print('Attempting to add meta_ad_id field...')
                        try:
                            # Add meta_ad_id field at least
                            Lead.write([leads[0]], {'meta_ad_id': ad_id})
                            print('✅ Added meta_ad_id to lead')
                        except Exception as e:
                            print(f'❌ Could not add meta_ad_id: {e}')
                else:
                    print(f'❌ Creative API error: {creative_response.text}')
            else:
                print('❌ No creative found in ad data')
        else:
            print(f'❌ Ad API error: {response.text}')
            
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == '__main__':
    print('Adding creative fields...')
    add_creative_fields()
    print('\nUpdating lead creative data...')
    update_lead_creative_data()