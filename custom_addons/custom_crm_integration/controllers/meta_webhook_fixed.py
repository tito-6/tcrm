from odoo import http
from odoo.http import request
import json
import logging
import requests
import os

_logger = logging.getLogger(__name__)


class MetaWebhookFixed(http.Controller):
    """Fixed Meta webhook controller for Odoo 17"""
    
    @http.route('/webhook/meta/fixed', type='http', auth='public', methods=['POST'], csrf=False)
    def meta_webhook_fixed(self, **kwargs):
        """Fixed webhook endpoint that works with Odoo 17"""
        try:
            # Properly read raw request data for Odoo 17
            raw_data = request.httprequest.data.decode('utf-8')
            data = json.loads(raw_data)
            _logger.info(f"📩 Received Meta webhook: {json.dumps(data, indent=2)}")
            
            # Extract lead information from Meta's payload
            if data.get('object') == 'page':
                for entry in data.get('entry', []):
                    for change in entry.get('changes', []):
                        if change.get('field') == 'leadgen':
                            value = change.get('value', {})
                            
                            # Fetch lead and creative data
                            lead_info = self._fetch_lead_data(value.get('leadgen_id'))
                            creative_info = self._fetch_ad_creative_data(value.get('ad_id'))
                            
                            lead_data = {
                                'name': lead_info.get('name') or f"Meta Lead - {value.get('leadgen_id', 'Unknown')}",
                                'email_from': lead_info.get('email'),
                                'phone': lead_info.get('phone'),
                                'description': f"""
                                    Lead Source: Meta (Facebook/Instagram)
                                    Lead ID: {value.get('leadgen_id')}
                                    Form ID: {value.get('form_id')}
                                    Ad ID: {value.get('ad_id')}
                                    Created: {value.get('created_time')}
                                    
                                    Form Responses: {json.dumps(lead_info.get('responses', {}), indent=2)}
                                """,
                                'type': 'lead',
                                # Meta fields
                                'meta_creative_id': creative_info.get('id'),
                                'meta_creative_type': creative_info.get('type'),
                                'meta_creative_media_url': creative_info.get('media_url'),
                                'meta_creative_body': creative_info.get('body'),
                                'meta_creative_title': creative_info.get('title'),
                                'meta_creative_cta': creative_info.get('cta'),
                            }
                            
                            # Create lead
                            lead = request.env['crm.lead'].sudo().create(lead_data)
                            _logger.info(f'✅ Created Meta lead with ID: {lead.id}')
            
            return request.make_json_response({'success': True})
            
        except Exception as e:
            _logger.error(f"❌ Error processing Meta lead: {str(e)}", exc_info=True)
            return request.make_json_response({'success': False, 'error': str(e)})
    
    def _fetch_lead_data(self, leadgen_id):
        """Fetch lead data from Meta Graph API"""
        if not leadgen_id:
            return {}
        
        access_token = os.environ.get('META_USER_ACCESS_TOKEN')
        if not access_token:
            return {}
        
        try:
            url = f"https://graph.facebook.com/v24.0/{leadgen_id}"
            params = {
                'access_token': access_token,
                'fields': 'id,created_time,field_data,platform'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Extract form responses
                responses = {}
                name_parts = []
                email = None
                phone = None
                
                for field in data.get('field_data', []):
                    field_name = field.get('name', '').lower()
                    field_values = field.get('values', [])
                    value = field_values[0] if field_values else ''
                    
                    responses[field_name] = value
                    
                    if field_name in ['first_name', 'ad', 'name', 'isim']:
                        name_parts.append(value)
                    elif field_name in ['last_name', 'soyad', 'surname']:
                        name_parts.append(value)
                    elif field_name in ['email', 'e_posta', 'e-posta']:
                        email = value
                    elif field_name in ['phone_number', 'telefon', 'phone']:
                        phone = value
                
                return {
                    'name': ' '.join(name_parts) if name_parts else None,
                    'email': email,
                    'phone': phone,
                    'responses': responses
                }
            return {}
        except:
            return {}
    
    def _fetch_ad_creative_data(self, ad_id):
        """Fetch ad creative data from Meta Graph API"""
        if not ad_id:
            return {}
        
        access_token = os.environ.get('META_USER_ACCESS_TOKEN')
        if not access_token:
            return {}
        
        try:
            # Get ad data with creative info
            ad_url = f"https://graph.facebook.com/v24.0/{ad_id}"
            ad_params = {
                'access_token': access_token,
                'fields': 'id,name,creative{id,object_story_spec,image_url,video_id,thumbnail_url}'
            }
            
            response = requests.get(ad_url, params=ad_params, timeout=10)
            if response.status_code == 200:
                ad_data = response.json()
                creative = ad_data.get('creative', {})
                
                if not creative.get('id'):
                    return {}
                
                # Get detailed creative data
                creative_url = f"https://graph.facebook.com/v24.0/{creative['id']}"
                creative_params = {
                    'access_token': access_token,
                    'fields': 'id,name,object_story_spec,image_url,video_id,thumbnail_url'
                }
                
                creative_response = requests.get(creative_url, params=creative_params, timeout=10)
                if creative_response.status_code == 200:
                    creative_data = creative_response.json()
                    
                    # Determine type and media URL
                    creative_type = 'image'
                    media_url = creative_data.get('image_url')
                    
                    if creative_data.get('video_id'):
                        creative_type = 'video'
                        media_url = creative_data.get('thumbnail_url')
                    
                    return {
                        'id': creative_data.get('id'),
                        'type': creative_type,
                        'media_url': media_url,
                        'body': None,  # Not available in basic fields
                        'title': None,  # Not available in basic fields  
                        'cta': None  # Not available in basic fields
                    }
            return {}
        except:
            return {}