# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from werkzeug.wrappers import Response
import logging
import os
import json
import requests

_logger = logging.getLogger(__name__)

class WebhooksController(http.Controller):

    @http.route(['/webhooks/meta'], type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def meta_webhook(self, **kwargs):
        _logger.info('meta_webhook called method=%s kwargs=%s', request.httprequest.method, kwargs)
        
        # Facebook/Meta verification handshake
        if request.httprequest.method == 'GET':
            hub_mode = kwargs.get('hub.mode')
            hub_challenge = kwargs.get('hub.challenge')
            hub_verify_token = kwargs.get('hub.verify_token')
            
            expected_token = os.environ.get('META_WEBHOOK_VERIFY_TOKEN', 'my_secure_meta_webhook_token_2024')
            
            if hub_mode == 'subscribe' and hub_challenge and hub_verify_token == expected_token:
                _logger.info('Meta webhook verification SUCCESS, responding with challenge=%s', hub_challenge)
                return hub_challenge
            else:
                _logger.warning('Meta webhook verification FAILED - mode=%s token_match=%s', hub_mode, hub_verify_token == expected_token)
                return Response('Forbidden', status=403)

        # Log POST payload
        try:
            raw = request.httprequest.get_data()
            _logger.info('Meta webhook payload: %s', raw[:2000])
            
            # Parse the webhook data
            data = json.loads(raw)
            
            # Process lead generation webhooks
            if data.get('object') == 'page':
                for entry in data.get('entry', []):
                    for change in entry.get('changes', []):
                        if change.get('field') == 'leadgen':
                            leadgen_value = change.get('value', {})
                            leadgen_id = leadgen_value.get('leadgen_id')
                            page_id = leadgen_value.get('page_id')
                            form_id = leadgen_value.get('form_id')
                            # Extract campaign data from webhook
                            ad_id = leadgen_value.get('ad_id')
                            adgroup_id = leadgen_value.get('adgroup_id')
                            campaign_id = leadgen_value.get('campaign_id')
                            
                            if leadgen_id:
                                _logger.info('Processing leadgen_id=%s from page=%s form=%s ad=%s campaign=%s', 
                                           leadgen_id, page_id, form_id, ad_id, campaign_id)
                                # Pass campaign data to lead creation
                                self._fetch_and_create_lead(
                                    leadgen_id, 
                                    page_id=page_id, 
                                    form_id=form_id, 
                                    ad_id=ad_id,
                                    adgroup_id=adgroup_id,
                                    campaign_id=campaign_id,
                                    raw_payload=raw.decode('utf-8', errors='ignore')
                                )
                            
        except Exception as e:
            _logger.exception('Error processing Meta webhook payload: %s', e)
        _logger.info('Meta webhook default OK response')
        return 'OK'

    def _fetch_and_create_lead(self, leadgen_id, page_id=None, form_id=None, ad_id=None, adgroup_id=None, campaign_id=None, raw_payload=None):
        """Fetch lead data from Meta Graph API and create in Odoo CRM"""
        try:
            # Get Meta credentials from environment
            user_access_token = os.environ.get('META_USER_ACCESS_TOKEN')
            
            if not user_access_token:
                _logger.error('META_USER_ACCESS_TOKEN not configured')
                return
            
            # Use user access token (required for lead data access)
            access_token = user_access_token
            
            # Fetch lead data from Graph API
            graph_url = f"https://graph.facebook.com/v24.0/{leadgen_id}"
            params = {'access_token': access_token}
            
            _logger.info('Fetching lead data from Graph API: %s', graph_url)
            response = requests.get(graph_url, params=params, timeout=10)
            response.raise_for_status()
            
            lead_data = response.json()
            _logger.info('Received lead data: %s', lead_data)
            
            # Extract lead information
            field_data = {item['name']: item['values'][0] for item in lead_data.get('field_data', [])}
            
            _logger.info('Extracted field data: %s', field_data)

            # Determine lead name with improved logic
            lead_name = None
            
            # Try various name field combinations
            name_fields = [
                'full_name', 'name', 'ad_name', 'customer_name', 'contact_name',
                'first_name_last_name', 'nombre_completo', 'isim_soyisim'
            ]
            
            for field in name_fields:
                if field_data.get(field):
                    lead_name = field_data[field].strip()
                    break
            
            # If no full name, try combining first and last name
            if not lead_name:
                first_name = field_data.get('first_name') or field_data.get('firstname') or field_data.get('ad') or ''
                last_name = field_data.get('last_name') or field_data.get('lastname') or field_data.get('soyad') or ''
                if first_name or last_name:
                    lead_name = f"{first_name} {last_name}".strip()
            
            # If still no name, try email username as name
            if not lead_name and field_data.get('email'):
                email = field_data.get('email')
                if '@' in email:
                    email_username = email.split('@')[0]
                    # Clean up email username (remove dots, numbers if it looks like a name)
                    if not email_username.replace('.', '').replace('_', '').isdigit():
                        lead_name = email_username.replace('.', ' ').replace('_', ' ').title()
            
            # Final fallback
            if not lead_name:
                lead_name = 'Lead from Meta'
            
            _logger.info('Final lead name determined: %s', lead_name)
            
            # Create lead in Odoo CRM
            lead_vals = {
                'name': lead_name,
                'contact_name': lead_name,
                'email_from': field_data.get('email') or field_data.get('email_address') or '',
                'phone': field_data.get('phone_number') or field_data.get('phone') or field_data.get('mobile') or field_data.get('telefon') or '',
                'description': f"Lead from Meta Form\nForm ID: {lead_data.get('form_id')}\nCreated: {lead_data.get('created_time')}\n\nFull data: {json.dumps(field_data, indent=2)}",
                'source_id': request.env.ref('utm.utm_source_facebook').id if request.env.ref('utm.utm_source_facebook', False) else False,
            }

            # Add meta fields only if present on model (module installed)
            try:
                lead_model = request.env['crm.lead']
                if 'meta_leadgen_id' in lead_model._fields:
                    # Convert Facebook timestamp to datetime
                    from datetime import datetime
                    submitted_on = None
                    if lead_data.get('created_time'):
                        try:
                            # Facebook created_time is Unix timestamp
                            submitted_on = datetime.fromtimestamp(int(lead_data.get('created_time')))
                        except (ValueError, TypeError):
                            pass
                    
                    # Fetch campaign information
                    campaign_data = self._fetch_campaign_data(access_token, ad_id, adgroup_id, campaign_id)
                    
                    lead_vals.update({
                        'meta_leadgen_id': leadgen_id or lead_data.get('id'),
                        'meta_page_id': page_id or lead_data.get('page_id'),
                        'meta_form_id': form_id or lead_data.get('form_id'),
                        'meta_raw_payload': raw_payload or json.dumps(lead_data),
                        'meta_submitted_on': submitted_on,
                        'meta_ad_id': ad_id,
                        'meta_adset_id': adgroup_id,
                        'meta_campaign_id': campaign_id,
                        'meta_ad_name': campaign_data.get('ad_name'),
                        'meta_adset_name': campaign_data.get('adset_name'),
                        'meta_campaign_name': campaign_data.get('campaign_name'),
                        'meta_source': 'facebook',
                        'meta_medium': 'facebook_ads',
                    })
            except Exception:
                pass

            # Optional: assignment based on mapping rules if module installed
            try:
                mapping_model = request.env['meta.lead.mapping'].sudo()
                mapping = mapping_model.search([('active', '=', True), ('form_id', '=', lead_vals['meta_form_id'])], limit=1)
                if not mapping and lead_vals['meta_page_id']:
                    mapping = mapping_model.search([('active', '=', True), ('page_id', '=', lead_vals['meta_page_id']), ('form_id', '=', False)], limit=1)
                if not mapping:
                    mapping = mapping_model.search([('active', '=', True), ('page_id', '=', False), ('form_id', '=', False)], limit=1)

                if mapping:
                    if mapping.team_id:
                        lead_vals['team_id'] = mapping.team_id.id
                    if mapping.user_id:
                        lead_vals['user_id'] = mapping.user_id.id
            except Exception as e:
                _logger.debug('Meta mapping not applied (module not installed or other issue): %s', e)
            
            # Create the lead
            lead = request.env['crm.lead'].sudo().create(lead_vals)
            _logger.info('Created CRM lead id=%s for leadgen_id=%s', lead.id, leadgen_id)
            
        except requests.exceptions.RequestException as e:
            _logger.exception('Error fetching lead from Meta Graph API: %s', e)
        except Exception as e:
            _logger.exception('Error creating CRM lead: %s', e)

    def _fetch_campaign_data(self, access_token, ad_id=None, adset_id=None, campaign_id=None):
        """Fetch campaign, ad set, and ad details from Facebook Graph API"""
        campaign_data = {}
        
        try:
            # Fetch Ad information
            if ad_id:
                ad_url = f"https://graph.facebook.com/v24.0/{ad_id}"
                ad_params = {'access_token': access_token, 'fields': 'name,adset_id,campaign_id'}
                ad_response = requests.get(ad_url, params=ad_params, timeout=10)
                if ad_response.status_code == 200:
                    ad_data = ad_response.json()
                    campaign_data['ad_name'] = ad_data.get('name')
                    # Update IDs from ad data if not provided
                    if not adset_id:
                        adset_id = ad_data.get('adset_id')
                    if not campaign_id:
                        campaign_id = ad_data.get('campaign_id')
                    _logger.info('Fetched ad data: %s', ad_data)
                else:
                    _logger.warning('Failed to fetch ad data for %s: %s', ad_id, ad_response.text)
            
            # Fetch Ad Set information
            if adset_id:
                adset_url = f"https://graph.facebook.com/v24.0/{adset_id}"
                adset_params = {'access_token': access_token, 'fields': 'name,campaign_id'}
                adset_response = requests.get(adset_url, params=adset_params, timeout=10)
                if adset_response.status_code == 200:
                    adset_data = adset_response.json()
                    campaign_data['adset_name'] = adset_data.get('name')
                    # Update campaign ID if not provided
                    if not campaign_id:
                        campaign_id = adset_data.get('campaign_id')
                    _logger.info('Fetched adset data: %s', adset_data)
                else:
                    _logger.warning('Failed to fetch adset data for %s: %s', adset_id, adset_response.text)
            
            # Fetch Campaign information
            if campaign_id:
                campaign_url = f"https://graph.facebook.com/v24.0/{campaign_id}"
                campaign_params = {'access_token': access_token, 'fields': 'name,objective,status'}
                campaign_response = requests.get(campaign_url, params=campaign_params, timeout=10)
                if campaign_response.status_code == 200:
                    campaign_info = campaign_response.json()
                    campaign_data['campaign_name'] = campaign_info.get('name')
                    campaign_data['campaign_objective'] = campaign_info.get('objective')
                    campaign_data['campaign_status'] = campaign_info.get('status')
                    _logger.info('Fetched campaign data: %s', campaign_info)
                else:
                    _logger.warning('Failed to fetch campaign data for %s: %s', campaign_id, campaign_response.text)
        
        except requests.exceptions.RequestException as e:
            _logger.warning('Error fetching campaign data from Meta Graph API: %s', e)
        except Exception as e:
            _logger.warning('Unexpected error fetching campaign data: %s', e)
        
        return campaign_data

    @http.route(['/webhooks/google'], type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def google_webhook(self, **kwargs):
        _logger.info('google_webhook called method=%s kwargs=%s', request.httprequest.method, kwargs)
        # Some Google webhook setups may require a validation key via GET for testing
        if request.httprequest.method == 'GET':
            _logger.info('Google webhook GET verification params: %s', kwargs)
            return 'OK'

        # Log POST payload
        try:
            raw = request.httprequest.get_data()
            _logger.info('Google webhook payload: %s', raw[:2000])
        except Exception as e:
            _logger.exception('Error reading Google webhook payload: %s', e)
        _logger.info('Google webhook default OK response')
        return 'OK'
