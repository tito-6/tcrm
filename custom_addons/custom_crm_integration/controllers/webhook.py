# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging
import hashlib
import hmac
import requests
import os

_logger = logging.getLogger(__name__)


class LeadWebhook(http.Controller):
    """Webhook endpoints for external lead sources"""
    
    def _fetch_lead_data(self, leadgen_id):
        """Fetch lead data from Meta Graph API"""
        if not leadgen_id:
            return {}
        
        access_token = os.environ.get('META_USER_ACCESS_TOKEN')
        if not access_token:
            _logger.warning('Meta access token not configured')
            return {}
        
        try:
            url = f"https://graph.facebook.com/v24.0/{leadgen_id}"
            params = {
                'access_token': access_token,
                'fields': 'id,created_time,field_data,is_organic,platform'
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
                    
                    # Map Turkish field names to English
                    if field_name in ['first_name', 'ad', 'name', 'isim']:
                        name_parts.append(value)
                    elif field_name in ['last_name', 'soyad', 'surname']:
                        name_parts.append(value)
                    elif field_name in ['email', 'e_posta', 'e-posta']:
                        email = value
                    elif field_name in ['phone_number', 'telefon', 'phone', 'tel']:
                        phone = value
                
                return {
                    'name': ' '.join(name_parts) if name_parts else None,
                    'email': email,
                    'phone': phone,
                    'platform': data.get('platform', 'facebook'),
                    'responses': responses,
                    'created_time': data.get('created_time')
                }
            else:
                _logger.error(f"Error fetching lead data: {response.text}")
                return {}
                
        except Exception as e:
            _logger.error(f"Exception fetching lead data: {str(e)}")
            return {}
    
    def _fetch_ad_creative_data(self, ad_id):
        """Fetch ad creative data from Meta Graph API"""
        if not ad_id:
            return {}
        
        access_token = os.environ.get('META_USER_ACCESS_TOKEN')
        if not access_token:
            _logger.warning('Meta access token not configured')
            return {}
        
        try:
            # First get ad data with creative info
            ad_url = f"https://graph.facebook.com/v24.0/{ad_id}"
            ad_params = {
                'access_token': access_token,
                'fields': 'id,name,status,creative{id,object_story_spec,image_url,video_id,thumbnail_url}'
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
                    'fields': 'id,name,object_story_spec,image_url,video_id,thumbnail_url,body,title'
                }
                
                creative_response = requests.get(creative_url, params=creative_params, timeout=10)
                if creative_response.status_code == 200:
                    creative_data = creative_response.json()
                    
                    # Determine creative type and media URL
                    creative_type = 'image'
                    media_url = creative_data.get('image_url')
                    
                    if creative_data.get('video_id'):
                        creative_type = 'video'
                        media_url = creative_data.get('thumbnail_url')
                    
                    # Extract CTA from object_story_spec
                    cta = None
                    object_story = creative_data.get('object_story_spec', {})
                    if 'link_data' in object_story:
                        link_data = object_story['link_data']
                        cta = link_data.get('call_to_action', {}).get('type')
                    
                    return {
                        'id': creative_data.get('id'),
                        'type': creative_type,
                        'media_url': media_url,
                        'body': creative_data.get('body'),
                        'title': creative_data.get('title'),
                        'cta': cta
                    }
                else:
                    _logger.error(f"Error fetching creative details: {creative_response.text}")
                    return {}
            else:
                _logger.error(f"Error fetching ad data: {response.text}")
                return {}
                
        except Exception as e:
            _logger.error(f"Exception fetching creative data: {str(e)}")
            return {}
    
    # ===== META (FACEBOOK/INSTAGRAM) WEBHOOK =====
    
    @http.route('/webhook/meta/verify', type='http', auth='public', methods=['GET'], csrf=False)
    def verify_meta_webhook(self, **kwargs):
        """
        Verify Meta webhook endpoint
        Meta sends a GET request to verify the endpoint
        """
        verify_token = "odoo_meta_webhook_2025"  # Change this to your own secret token
        
        mode = kwargs.get('hub.mode')
        token = kwargs.get('hub.verify_token')
        challenge = kwargs.get('hub.challenge')
        
        if mode == 'subscribe' and token == verify_token:
            _logger.info('Meta webhook verified successfully')
            return challenge
        else:
            _logger.warning('Meta webhook verification failed')
            return http.Response('Verification failed', status=403)
    
    @http.route('/webhook/meta/leads', type='http', auth='public', methods=['POST'], csrf=False)
    def receive_meta_lead(self, **kwargs):
        """
        Receive leads from Meta (Facebook/Instagram) Lead Ads
        
        Expected payload from Meta:
        {
            "object": "page",
            "entry": [{
                "id": "page_id",
                "time": 1234567890,
                "changes": [{
                    "value": {
                        "leadgen_id": "123456",
                        "page_id": "page_id",
                        "form_id": "form_id",
                        "adgroup_id": "adgroup_id",
                        "ad_id": "ad_id",
                        "created_time": "2025-10-30T12:00:00+0000"
                    },
                    "field": "leadgen"
                }]
            }]
        }
        """
        try:
            # Properly read raw request data for Odoo 17
            raw_data = request.httprequest.data.decode('utf-8')
            data = json.loads(raw_data)
            _logger.info(f"Received Meta webhook data: {json.dumps(data, indent=2)}")
            
            # Extract lead information from Meta's payload
            if data.get('object') == 'page':
                for entry in data.get('entry', []):
                    for change in entry.get('changes', []):
                        if change.get('field') == 'leadgen':
                            value = change.get('value', {})
                            
                            # Fetch actual lead data and creative info using Graph API
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
                                    Ad Group ID: {value.get('adgroup_id')}
                                    Page ID: {value.get('page_id')}
                                    Created: {value.get('created_time')}
                                    
                                    Form Responses: {json.dumps(lead_info.get('responses', {}), indent=2)}
                                """,
                                'type': 'lead',
                                # Meta fields
                                'meta_form_id': value.get('form_id'),
                                'meta_ad_id': value.get('ad_id'),
                                'meta_leadgen_id': value.get('leadgen_id'),
                                'meta_page_id': value.get('page_id'),
                                'meta_adset_id': value.get('adgroup_id'),
                                'meta_platform': lead_info.get('platform', 'facebook'),
                                # Creative fields
                                'meta_creative_id': creative_info.get('id'),
                                'meta_creative_type': creative_info.get('type'),
                                'meta_creative_media_url': creative_info.get('media_url'),
                                'meta_creative_body': creative_info.get('body'),
                                'meta_creative_title': creative_info.get('title'),
                                'meta_creative_cta': creative_info.get('cta'),
                            }
                            
                            # Try to get or create Meta source
                            try:
                                source = request.env.ref('utm.utm_source_facebook')
                                lead_data['source_id'] = source.id
                            except:
                                _logger.warning('Facebook UTM source not found')
                            
                            # Create lead
                            lead = request.env['crm.lead'].sudo().create(lead_data)
                            _logger.info(f'Created Meta lead with ID: {lead.id}')
            
            return request.make_json_response({'success': True, 'lead_id': lead.id})
            
        except Exception as e:
            _logger.error(f"Error processing Meta lead: {str(e)}", exc_info=True)
            return request.make_json_response({'success': False, 'error': str(e)})
    
    # ===== GOOGLE ADS WEBHOOK =====
    
    @http.route('/webhook/google/leads', type='http', auth='public', methods=['POST'], csrf=False)
    def receive_google_lead(self, **kwargs):
        """
        Receive leads from Google Ads
        
        Expected payload:
        {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john@example.com",
            "phoneNumber": "+1234567890",
            "campaignId": "campaign_123",
            "adGroupId": "adgroup_456",
            "gclid": "click_id",
            "customFields": {...}
        }
        """
        try:
            raw_data = request.httprequest.data.decode('utf-8')
            data = json.loads(raw_data)
            _logger.info(f"Received Google lead: {json.dumps(data, indent=2)}")
            
            # Extract lead data
            first_name = data.get('firstName', '')
            last_name = data.get('lastName', '')
            full_name = f"{first_name} {last_name}".strip() or 'Google Lead'
            
            lead_data = {
                'name': full_name,
                'contact_name': full_name,
                'email_from': data.get('email'),
                'phone': data.get('phoneNumber'),
                'description': f"""
                    Lead Source: Google Ads
                    Campaign ID: {data.get('campaignId')}
                    Ad Group ID: {data.get('adGroupId')}
                    GCLID: {data.get('gclid')}
                    
                    Custom Fields: {json.dumps(data.get('customFields', {}), indent=2)}
                """,
                'type': 'lead',
            }
            
            # Try to get or create Google source
            try:
                source = request.env.ref('utm.utm_source_adwords')
                lead_data['source_id'] = source.id
            except:
                _logger.warning('Google Ads UTM source not found')
            
            # Create lead
            lead = request.env['crm.lead'].sudo().create(lead_data)
            _logger.info(f'Created Google lead with ID: {lead.id}')
            
            return request.make_json_response({'success': True, 'lead_id': lead.id})
            
        except Exception as e:
            _logger.error(f"Error processing Google lead: {str(e)}", exc_info=True)
            return request.make_json_response({'success': False, 'error': str(e)})
    
    # ===== GENERIC WEBHOOK =====
    
    @http.route('/webhook/lead/create', type='http', auth='public', methods=['POST'], csrf=False)
    def create_lead_generic(self, **kwargs):
        """
        Generic webhook endpoint for creating leads
        Can be used with Zapier, Make.com, or custom integrations
        
        Payload:
        {
            "name": "Lead Name",
            "email": "email@example.com",
            "phone": "+1234567890",
            "company": "Company Name",
            "description": "Additional notes",
            "source": "facebook|google|website|other",
            "utm_source": "facebook",
            "utm_medium": "cpc",
            "utm_campaign": "summer_campaign"
        }
        """
        try:
            raw_data = request.httprequest.data.decode('utf-8')
            data = json.loads(raw_data)
            _logger.info(f"Received generic lead: {json.dumps(data, indent=2)}")
            
            lead_data = {
                'name': data.get('name', 'Web Lead'),
                'contact_name': data.get('name'),
                'email_from': data.get('email'),
                'phone': data.get('phone'),
                'partner_name': data.get('company'),
                'description': data.get('description', ''),
                'type': 'lead',
            }
            
            # Handle UTM tracking
            utm_source = data.get('utm_source') or data.get('source')
            if utm_source:
                # Try to find matching UTM source
                utm_obj = request.env['utm.source'].sudo()
                source_rec = utm_obj.search([('name', '=ilike', utm_source)], limit=1)
                if source_rec:
                    lead_data['source_id'] = source_rec.id
            
            # Create lead
            lead = request.env['crm.lead'].sudo().create(lead_data)
            _logger.info(f'Created generic lead with ID: {lead.id}')
            
            return request.make_json_response({
                'success': True,
                'lead_id': lead.id,
                'message': f'Lead "{lead.name}" created successfully'
            })
            
        except Exception as e:
            _logger.error(f"Error creating lead: {str(e)}", exc_info=True)
            return request.make_json_response({'success': False, 'error': str(e)})
    
    # ===== TEST ENDPOINT =====
    
    @http.route('/webhook/test', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def test_webhook(self, **kwargs):
        """Test endpoint to verify webhooks are working"""
        return {
            'status': 'ok',
            'message': 'Webhook endpoint is working',
            'timestamp': str(request.env['ir.sequence'].sudo().get_datetime_now()),
            'available_endpoints': [
                '/webhook/meta/verify (GET)',
                '/webhook/meta/leads (POST)',
                '/webhook/google/leads (POST)',
                '/webhook/lead/create (POST)',
            ]
        }
