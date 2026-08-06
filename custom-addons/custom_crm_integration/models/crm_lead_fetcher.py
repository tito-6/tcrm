# -*- coding: utf-8 -*-
try:
    from tcrm import models, fields, api
except ImportError:
    from odoo import models, fields, api
import requests
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class CrmLeadFetcher(models.Model):
    _name = 'crm.lead.fetcher'
    _description = 'Facebook Lead Fetcher Service'

    def _get_config_value(self, param_name):
        """Get configuration parameter value"""
        return self.env['ir.config_parameter'].sudo().get_param(
            f'custom_crm_integration.{param_name}'
        )

    def _set_config_value(self, param_name, value):
        """Set configuration parameter value"""
        self.env['ir.config_parameter'].sudo().set_param(
            f'custom_crm_integration.{param_name}', value
        )

    def _get_page_access_token(self, page_id, user_token):
        """Get page access token for a specific page"""
        url = f"https://graph.facebook.com/v21.0/{page_id}"
        params = {
            'fields': 'access_token',
            'access_token': user_token
        }
        
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            raise Exception(f"Failed to get page token: {response.text}")

    def _get_leadgen_forms(self, page_id, page_token):
        """Get all lead generation forms for a page"""
        url = f"https://graph.facebook.com/v21.0/{page_id}/leadgen_forms"
        params = {
            'access_token': page_token,
            'fields': 'id,name,status,leads_count'
        }
        
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json().get('data', [])
        else:
            raise Exception(f"Failed to get forms: {response.text}")

    def _fetch_form_leads(self, form_id, page_token):
        """Fetch leads from a specific form"""
        leads_url = f"https://graph.facebook.com/v21.0/{form_id}/leads"
        leads_params = {
            'access_token': page_token,
            'fields': 'id,created_time,field_data,ad_id,adset_id,campaign_id,form_id,ad_name,adset_name,campaign_name,platform',
            'limit': 500
        }
        
        all_leads = []
        
        while leads_url:
            response = requests.get(leads_url, params=leads_params, timeout=30)
            if response.status_code != 200:
                _logger.error(f"Failed to fetch leads from form {form_id}: {response.text}")
                break
            
            data = response.json()
            if 'data' in data and data['data']:
                all_leads.extend(data['data'])
                
                # Check for next page
                if 'paging' in data and 'next' in data['paging']:
                    leads_url = data['paging']['next']
                    leads_params = {}
                else:
                    leads_url = None
            else:
                leads_url = None
        
        return all_leads

    def _extract_lead_data(self, lead_data):
        """Extract and map lead field data"""
        field_data = {}
        raw_field_data = lead_data.get('field_data', [])
        
        for item in raw_field_data:
            field_name = item.get('name', '')
            field_values = item.get('values', [])
            if field_values:
                field_data[field_name] = field_values[0]
        
        # Extract name
        name = ''
        for key in ['full_name', 'name', 'adı_soyadı', 'adi_soyadi', 'ad_soyad']:
            if key in field_data:
                name = field_data[key]
                break
        
        if not name and 'first_name' in field_data:
            name = f"{field_data.get('first_name', '')} {field_data.get('last_name', '')}".strip()
        
        # Extract email
        email = ''
        for key in ['email', 'e_mail', 'e-mail', 'e-posta', 'e_posta', 'eposta']:
            if key in field_data:
                email = field_data[key]
                break
        
        # Extract phone
        phone = ''
        for key in field_data.keys():
            key_lower = key.lower()
            if any(word in key_lower for word in ['phone', 'telefon', 'tel', 'numara', 'iletişim', 'mobile']):
                phone = field_data[key]
                break
        
        return {
            'name': name,
            'email': email,
            'phone': phone,
            'field_data': field_data
        }

    def _create_lead_in_odoo(self, lead_data, page_name):
        """Create a lead in Odoo CRM"""
        meta_lead_id = lead_data.get('id')
        
        # Check if lead already exists
        existing = self.env['crm.lead'].search([
            ('description', 'ilike', f'Lead ID: {meta_lead_id}')
        ], limit=1)
        
        if existing:
            return False  # Lead already exists
        
        # Extract data
        extracted = self._extract_lead_data(lead_data)
        
        # Build description
        description_parts = [
            f"Lead from {page_name}",
            f"Lead ID: {meta_lead_id}",
            f"Submitted On: {lead_data.get('created_time', 'Unknown')}",
            ""
        ]
        
        if lead_data.get('campaign_name'):
            description_parts.append(f"Campaign: {lead_data.get('campaign_name')}")
        if lead_data.get('adset_name'):
            description_parts.append(f"Ad Set: {lead_data.get('adset_name')}")
        if lead_data.get('ad_name'):
            description_parts.append(f"Ad: {lead_data.get('ad_name')}")
        if lead_data.get('platform'):
            description_parts.append(f"Platform: {lead_data.get('platform')}")
        
        if extracted['field_data']:
            description_parts.append("")
            description_parts.append("Form Answers:")
            for key, value in extracted['field_data'].items():
                description_parts.append(f"  • {key}: {value}")
        
        # Prepare lead values
        final_name = extracted['name'] if extracted['name'] else f"Lead {meta_lead_id}"
        
        # Parse submitted date
        submitted_on = lead_data.get('created_time', '')
        if submitted_on:
            try:
                dt = datetime.fromisoformat(submitted_on.replace('Z', '+00:00'))
                submitted_on = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                submitted_on = False
        
        # Map platform
        platform_raw = lead_data.get('platform', '')
        platform_mapping = {
            'fb': 'facebook',
            'ig': 'instagram',
            'm': 'messenger',
            'facebook': 'facebook',
            'instagram': 'instagram',
            'messenger': 'messenger'
        }
        platform = platform_mapping.get(platform_raw.lower(), False) if platform_raw else False
        
        lead_values = {
            'name': final_name,
            'contact_name': extracted['name'] if extracted['name'] else '',
            'email_from': extracted['email'],
            'phone': extracted['phone'],
            'description': '\n'.join(description_parts),
            'type': 'lead',
            'meta_campaign_id': lead_data.get('campaign_id', ''),
            'meta_campaign_name': lead_data.get('campaign_name', ''),
            'meta_adset_id': lead_data.get('adset_id', ''),
            'meta_adset_name': lead_data.get('adset_name', ''),
            'meta_ad_id': lead_data.get('ad_id', ''),
            'meta_ad_name': lead_data.get('ad_name', ''),
            'meta_form_id': lead_data.get('form_id', ''),
            'meta_platform': platform,
            'submitted_on': submitted_on,
        }
        
        # Create lead
        self.env['crm.lead'].create(lead_values)
        return True

    @api.model
    def fetch_leads_from_meta(self):
        """Main method to fetch leads from Facebook"""
        _logger.info("Starting Meta lead fetch...")
        
        # Get configuration
        user_token = self._get_config_value('meta_user_access_token')
        page_id = self._get_config_value('meta_page_id')
        
        if not user_token or not page_id:
            _logger.warning("Meta credentials not configured")
            return {'success': False, 'error': 'Configuration missing'}
        
        try:
            # Get page access token
            page_token = self._get_page_access_token(page_id, user_token)
            
            # Get all forms
            forms = self._get_leadgen_forms(page_id, page_token)
            
            # Get page name
            page_response = requests.get(
                f"https://graph.facebook.com/v21.0/{page_id}",
                params={'access_token': user_token, 'fields': 'name'},
                timeout=30
            )
            page_name = page_response.json().get('name', 'Facebook Page')
            
            # Fetch leads from all forms
            total_leads = 0
            new_leads = 0
            
            for form in forms:
                form_leads = self._fetch_form_leads(form['id'], page_token)
                total_leads += len(form_leads)
                
                for lead_data in form_leads:
                    if self._create_lead_in_odoo(lead_data, page_name):
                        new_leads += 1
            
            # Update statistics
            self._set_config_value('meta_last_fetch_time', fields.Datetime.now())
            current_total = int(self._get_config_value('meta_total_leads_fetched') or 0)
            self._set_config_value('meta_total_leads_fetched', current_total + new_leads)
            
            _logger.info(f"Meta lead fetch complete: {new_leads} new leads out of {total_leads} total")
            
            return {
                'success': True,
                'new_leads': new_leads,
                'total_leads': total_leads
            }
            
        except Exception as e:
            _logger.error(f"Meta lead fetch failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    @api.model
    def cron_fetch_meta_leads(self):
        """Cron job to automatically fetch leads"""
        if self._get_config_value('meta_auto_fetch_enabled') == 'True':
            self.fetch_leads_from_meta()
