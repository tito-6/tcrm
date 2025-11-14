# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging
import requests
import os
import hashlib
import hmac

_logger = logging.getLogger(__name__)


class MetaLeadWebhook(http.Controller):
    """Enhanced Meta Leads webhook with real-time ad creative fetching"""
    
    def _get_meta_access_token(self):
        """Get Meta access token from environment or system parameters"""
        # Try environment variable first
        token = os.environ.get('META_USER_ACCESS_TOKEN')
        if token:
            return token
        
        # Try system parameters as fallback
        try:
            IrConfigParameter = request.env['ir.config_parameter'].sudo()
            token = IrConfigParameter.get_param('meta_leads.access_token')
            return token
        except Exception:
            return None
    
    def _fetch_lead_data(self, leadgen_id, access_token):
        """Fetch lead data from Meta Graph API"""
        try:
            url = f"https://graph.facebook.com/v24.0/{leadgen_id}"
            params = {
                'access_token': access_token,
                'fields': 'id,ad_id,adset_id,campaign_id,form_id,page_id,created_time,field_data'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                _logger.error(f"Error fetching lead data: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            _logger.error(f"Exception fetching lead data: {str(e)}")
            return None
    
    def _fetch_ad_creative_data(self, ad_id, access_token):
        """Fetch ad creative data from Meta Graph API"""
        try:
            # First get the ad and its creative
            ad_url = f"https://graph.facebook.com/v24.0/{ad_id}"
            ad_params = {
                'access_token': access_token,
                'fields': 'id,name,status,creative{id,object_story_spec,image_url,video_id,thumbnail_url}'
            }
            
            ad_response = requests.get(ad_url, params=ad_params, timeout=10)
            if ad_response.status_code != 200:
                _logger.error(f"Error fetching ad data: {ad_response.status_code} - {ad_response.text}")
                return None
                
            ad_data = ad_response.json()
            creative_info = ad_data.get('creative', {})
            
            # If we have a creative ID, get more details
            if creative_info.get('id'):
                creative_id = creative_info['id']
                creative_url = f"https://graph.facebook.com/v24.0/{creative_id}"
                creative_params = {
                    'access_token': access_token,
                    'fields': 'id,name,object_story_spec,image_url,video_id,thumbnail_url,body,title'
                }
                
                creative_response = requests.get(creative_url, params=creative_params, timeout=10)
                if creative_response.status_code == 200:
                    creative_data = creative_response.json()
                    # Merge ad data with creative data
                    return {
                        'ad_id': ad_data.get('id'),
                        'ad_name': ad_data.get('name'),
                        'ad_status': ad_data.get('status'),
                        'creative_id': creative_data.get('id'),
                        'creative_name': creative_data.get('name'),
                        'image_url': creative_data.get('image_url'),
                        'video_id': creative_data.get('video_id'),
                        'thumbnail_url': creative_data.get('thumbnail_url'),
                        'body': creative_data.get('body'),
                        'title': creative_data.get('title'),
                        'object_story_spec': creative_data.get('object_story_spec', {})
                    }
            
            # Return basic ad data if creative fetch fails
            return {
                'ad_id': ad_data.get('id'),
                'ad_name': ad_data.get('name'),
                'ad_status': ad_data.get('status'),
                'creative_id': creative_info.get('id'),
                'image_url': creative_info.get('image_url'),
                'video_id': creative_info.get('video_id'),
                'thumbnail_url': creative_info.get('thumbnail_url')
            }
            
        except Exception as e:
            _logger.error(f"Exception fetching ad creative: {str(e)}")
            return None
    
    def _get_video_thumbnail(self, video_id, access_token):
        """Get video thumbnail URL"""
        try:
            video_url = f"https://graph.facebook.com/v24.0/{video_id}"
            video_params = {
                'access_token': access_token,
                'fields': 'thumbnails.limit(1){uri},picture'
            }
            
            response = requests.get(video_url, params=video_params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Try thumbnails first
                thumbnails = data.get('thumbnails', {}).get('data', [])
                if thumbnails:
                    return thumbnails[0].get('uri')
                
                # Fallback to picture
                return data.get('picture')
            
            return None
            
        except Exception as e:
            _logger.error(f"Error fetching video thumbnail: {str(e)}")
            return None
    
    def _extract_field_data(self, field_data):
        """Extract and format lead field data"""
        extracted = {
            'name': None,
            'email': None,
            'phone': None,
            'company': None,
            'city': None,
            'message': None,
            'form_answers': []
        }
        
        # Field mapping for Turkish and English
        field_mapping = {
            'name': ['full_name', 'name', 'ad_soyad', 'isim_soyisim', 'ad_soyadi', 'tam_ad'],
            'email': ['email', 'e_posta', 'eposta', 'e-posta', 'mail_adresi'],
            'phone': ['phone_number', 'telefon', 'telefon_numarasi', 'phone', 'mobile_phone'],
            'company': ['company_name', 'sirket_adi', 'firma_adi', 'company', 'work_company'],
            'city': ['city', 'sehir', 'il', 'location'],
            'message': ['message', 'mesaj', 'yorum', 'not', 'additional_info']
        }
        
        for field in field_data:
            question = field.get('name', '').lower()
            value = field.get('values', [])
            if value:
                value_str = value[0] if isinstance(value, list) else str(value)
                
                # Add to form answers
                extracted['form_answers'].append({
                    'question': field.get('name', 'Question'),
                    'answer': value_str
                })
                
                # Map to standard fields
                for field_type, keywords in field_mapping.items():
                    if any(keyword in question for keyword in keywords):
                        if not extracted[field_type]:  # Don't override if already set
                            extracted[field_type] = value_str
                        break
        
        return extracted
    
    def _format_form_answers(self, form_answers):
        """Format form answers for display"""
        if not form_answers:
            return "No form responses available"
        
        formatted = "=== CLIENT FORM RESPONSES ===\\n\\n"
        for i, answer in enumerate(form_answers, 1):
            formatted += f"{i}. {answer['question']}: {answer['answer']}\\n"
        
        formatted += f"\\n--- Form completed with {len(form_answers)} questions ---"
        return formatted
    
    def _detect_platform(self, campaign_name="", ad_name="", adset_name=""):
        """Detect if lead comes from Instagram or Facebook"""
        text_to_check = f"{campaign_name} {ad_name} {adset_name}".lower()
        
        instagram_indicators = ['instagram', 'ig_', 'insta_', 'reels', 'stories']
        
        if any(indicator in text_to_check for indicator in instagram_indicators):
            return 'instagram', 'instagram_ads'
        else:
            return 'facebook', 'facebook_ads'
    
    @http.route('/webhook/meta/verify', type='http', auth='public', methods=['GET'], csrf=False)
    def verify_meta_webhook(self, **kwargs):
        """Verify Meta webhook endpoint"""
        verify_token = os.environ.get('META_WEBHOOK_VERIFY_TOKEN', 'my_secure_meta_webhook_token_2024')
        
        mode = kwargs.get('hub.mode')
        token = kwargs.get('hub.verify_token')
        challenge = kwargs.get('hub.challenge')
        
        if mode == 'subscribe' and token == verify_token:
            _logger.info('Meta webhook verified successfully')
            return challenge
        else:
            _logger.warning(f'Meta webhook verification failed. Mode: {mode}, Token: {token}')
            return http.Response('Verification failed', status=403)
    
    @http.route('/webhook/meta/leads', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_meta_lead(self, **kwargs):
        """
        Enhanced Meta webhook with real-time ad creative fetching
        """
        try:
            data = request.jsonrequest
            _logger.info(f"Received Meta webhook: {json.dumps(data, indent=2)}")
            
            access_token = self._get_meta_access_token()
            if not access_token:
                _logger.error("Meta access token not found")
                return {'success': False, 'error': 'Access token not configured'}
            
            leads_created = []
            
            # Process webhook payload
            if data.get('object') == 'page':
                for entry in data.get('entry', []):
                    for change in entry.get('changes', []):
                        if change.get('field') == 'leadgen':
                            value = change.get('value', {})
                            leadgen_id = value.get('leadgen_id')
                            ad_id = value.get('ad_id')
                            
                            if not leadgen_id:
                                continue
                            
                            _logger.info(f"Processing lead: {leadgen_id}, ad: {ad_id}")
                            
                            # Fetch full lead data from Meta
                            lead_data = self._fetch_lead_data(leadgen_id, access_token)
                            if not lead_data:
                                _logger.error(f"Could not fetch lead data for {leadgen_id}")
                                continue
                            
                            # Extract field data
                            field_data = lead_data.get('field_data', [])
                            extracted = self._extract_field_data(field_data)
                            
                            # Fetch ad creative data
                            creative_data = None
                            if ad_id:
                                creative_data = self._fetch_ad_creative_data(ad_id, access_token)
                            
                            # Detect platform (Instagram vs Facebook)
                            campaign_name = ""  # We'd get this from campaign API if needed
                            ad_name = creative_data.get('ad_name', '') if creative_data else ''
                            source, medium = self._detect_platform(campaign_name, ad_name)
                            
                            # Prepare lead data for Odoo
                            lead_name = extracted.get('name') or f"Meta Lead - {leadgen_id}"
                            
                            odoo_lead_data = {
                                'name': lead_name,
                                'contact_name': extracted.get('name'),
                                'email_from': extracted.get('email'),
                                'phone': extracted.get('phone'),
                                'partner_name': extracted.get('company'),
                                'city': extracted.get('city'),
                                'description': extracted.get('message', ''),
                                'type': 'lead',
                                
                                # Meta specific fields
                                'meta_leadgen_id': leadgen_id,
                                'meta_ad_id': ad_id,
                                'meta_adset_id': lead_data.get('adset_id'),
                                'meta_campaign_id': lead_data.get('campaign_id'),
                                'meta_form_id': lead_data.get('form_id'),
                                'meta_page_id': lead_data.get('page_id'),
                                'meta_platform': source,
                                'meta_form_answers': self._format_form_answers(extracted['form_answers']),
                                
                                # UTM tracking
                                'source_id': self._get_or_create_utm_source(source).id,
                                'medium_id': self._get_or_create_utm_medium(medium).id,
                            }
                            
                            # Add creative data if available
                            if creative_data:
                                # Get media URL (image or video thumbnail)
                                media_url = None
                                if creative_data.get('image_url'):
                                    media_url = creative_data['image_url']
                                elif creative_data.get('video_id'):
                                    media_url = self._get_video_thumbnail(creative_data['video_id'], access_token)
                                elif creative_data.get('thumbnail_url'):
                                    media_url = creative_data['thumbnail_url']
                                
                                # Add creative fields
                                odoo_lead_data.update({
                                    'meta_ad_name': creative_data.get('ad_name'),
                                    'meta_creative_id': creative_data.get('creative_id'),
                                    'meta_creative_body': creative_data.get('body'),
                                    'meta_creative_title': creative_data.get('title'),
                                    'meta_creative_media_url': media_url,
                                    'meta_creative_type': 'video' if creative_data.get('video_id') else 'image',
                                })
                                
                                # Extract call-to-action from object_story_spec
                                story_spec = creative_data.get('object_story_spec', {})
                                if story_spec.get('page_post_data', {}).get('call_to_action'):
                                    cta = story_spec['page_post_data']['call_to_action']
                                    odoo_lead_data['meta_creative_cta'] = cta.get('type', '')
                            
                            # Create lead in Odoo
                            lead = request.env['crm.lead'].sudo().create(odoo_lead_data)
                            leads_created.append(lead.id)
                            
                            _logger.info(f"Created lead {lead.id}: {lead.name} with creative data")
            
            return {
                'success': True,
                'leads_created': leads_created,
                'count': len(leads_created)
            }
            
        except Exception as e:
            _logger.error(f"Error processing Meta webhook: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _get_or_create_utm_source(self, source_name):
        """Get or create UTM source"""
        try:
            UTMSource = request.env['utm.source'].sudo()
            source = UTMSource.search([('name', '=', source_name)], limit=1)
            if not source:
                source = UTMSource.create({'name': source_name})
            return source
        except Exception:
            # Return default if creation fails
            return request.env.ref('utm.utm_source_direct', raise_if_not_found=False) or request.env['utm.source'].sudo().create({'name': 'direct'})
    
    def _get_or_create_utm_medium(self, medium_name):
        """Get or create UTM medium"""
        try:
            UTMMedium = request.env['utm.medium'].sudo()
            medium = UTMMedium.search([('name', '=', medium_name)], limit=1)
            if not medium:
                medium = UTMMedium.create({'name': medium_name})
            return medium
        except Exception:
            # Return default if creation fails
            return request.env.ref('utm.utm_medium_email', raise_if_not_found=False) or request.env['utm.medium'].sudo().create({'name': 'organic'})
    
    @http.route('/webhook/meta/test', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def test_meta_webhook(self, **kwargs):
        """Test endpoint for Meta webhook"""
        access_token = self._get_meta_access_token()
        
        result = {
            'status': 'ok',
            'message': 'Meta webhook endpoint is working',
            'access_token_configured': bool(access_token),
            'endpoints': {
                'verify': '/webhook/meta/verify (GET)',
                'leads': '/webhook/meta/leads (POST)',
                'test': '/webhook/meta/test (GET/POST)'
            }
        }
        
        return http.Response(
            json.dumps(result, indent=2),
            content_type='application/json'
        )