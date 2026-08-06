# -*- coding: utf-8 -*-

import os
import json
import logging
import requests
import phonenumbers
from datetime import datetime
from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from phonenumbers import NumberParseException

_logger = logging.getLogger(__name__)

class WhatsAppBusinessService(models.TransientModel):
    """WhatsApp Business API Service using Meta Graph API"""
    _name = 'whatsapp.business.service'
    _description = 'WhatsApp Business API Service'
    
    @property
    def base_url(self):
        return "https://graph.facebook.com/v21.0"
    
    @property 
    def access_token(self):
        return os.getenv('WHATSAPP_ACCESS_TOKEN') or os.getenv('META_USER_ACCESS_TOKEN')
    
    @property
    def phone_number(self):
        return os.getenv('WHATSAPP_PHONE_NUMBER', '905377178182')
    
    @property
    def business_account_id(self):
        return os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID', '466109021426030')
    
    @property
    def phone_number_id(self):
        return os.getenv('WHATSAPP_PHONE_NUMBER_ID', '618749782822501')
    
    def _make_api_request(self, endpoint, method='GET', data=None, files=None):
        """Make authenticated API request to WhatsApp Business API"""
        try:
            url = f"{self.base_url}/{endpoint}"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
            }
            
            if method == 'POST' and data and not files:
                headers['Content-Type'] = 'application/json'
                data = json.dumps(data)
            
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                files=files,
                timeout=30
            )
            
            _logger.info(f"WhatsApp API {method} {endpoint}: {response.status_code}")
            
            if response.status_code not in [200, 201]:
                _logger.error(f"WhatsApp API Error: {response.text}")
                return {'error': response.text, 'status_code': response.status_code}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"WhatsApp API Request failed: {str(e)}")
            return {'error': str(e)}
        except Exception as e:
            _logger.error(f"Unexpected error in WhatsApp API: {str(e)}")
            return {'error': str(e)}
    
    def validate_phone_number(self, phone_number):
        """Validate and format phone number for WhatsApp"""
        try:
            # Parse the phone number
            parsed_number = phonenumbers.parse(phone_number, None)
            
            # Check if valid
            if not phonenumbers.is_valid_number(parsed_number):
                return False, "Invalid phone number format"
            
            # Format for WhatsApp (international format without + sign)
            formatted = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
            formatted = formatted.lstrip('+')  # Remove + sign
            
            return True, formatted
            
        except NumberParseException as e:
            return False, f"Phone number parsing error: {str(e)}"
        except Exception as e:
            return False, f"Phone validation error: {str(e)}"
    
    def send_text_message(self, to_phone, message_text):
        """Send a text message via WhatsApp Business API"""
        # Validate phone number
        is_valid, formatted_phone = self.validate_phone_number(to_phone)
        if not is_valid:
            raise ValidationError(_(f"Invalid phone number: {formatted_phone}"))
        
        # Prepare message data
        message_data = {
            "messaging_product": "whatsapp",
            "to": formatted_phone,
            "type": "text",
            "text": {
                "body": message_text
            }
        }
        
        # Send message
        endpoint = f"{self.phone_number_id}/messages"
        result = self._make_api_request(endpoint, method='POST', data=message_data)
        
        if 'error' in result:
            _logger.error(f"Failed to send WhatsApp message: {result['error']}")
            raise UserError(_(f"Failed to send WhatsApp message: {result['error']}"))
        
        return result
    
    def send_template_message(self, to_phone, template_name, language_code='en', parameters=None):
        """Send a template message via WhatsApp Business API"""
        # Validate phone number
        is_valid, formatted_phone = self.validate_phone_number(to_phone)
        if not is_valid:
            raise ValidationError(_(f"Invalid phone number: {formatted_phone}"))
        
        # Prepare template data
        template_data = {
            "name": template_name,
            "language": {
                "code": language_code
            }
        }
        
        # Add parameters if provided
        if parameters:
            template_data["components"] = [{
                "type": "body",
                "parameters": [{"type": "text", "text": param} for param in parameters]
            }]
        
        message_data = {
            "messaging_product": "whatsapp",
            "to": formatted_phone,
            "type": "template",
            "template": template_data
        }
        
        # Send message
        endpoint = f"{self.phone_number_id}/messages"
        result = self._make_api_request(endpoint, method='POST', data=message_data)
        
        if 'error' in result:
            _logger.error(f"Failed to send WhatsApp template: {result['error']}")
            raise UserError(_(f"Failed to send WhatsApp template: {result['error']}"))
        
        return result
    
    def send_media_message(self, to_phone, media_type, media_url, caption=None):
        """Send media message (image, document, etc.) via WhatsApp Business API"""
        # Validate phone number
        is_valid, formatted_phone = self.validate_phone_number(to_phone)
        if not is_valid:
            raise ValidationError(_(f"Invalid phone number: {formatted_phone}"))
        
        # Prepare media data
        media_data = {
            "link": media_url
        }
        
        if caption and media_type in ['image', 'video']:
            media_data["caption"] = caption
        
        message_data = {
            "messaging_product": "whatsapp",
            "to": formatted_phone,
            "type": media_type,
            media_type: media_data
        }
        
        # Send message
        endpoint = f"{self.phone_number_id}/messages"
        result = self._make_api_request(endpoint, method='POST', data=message_data)
        
        if 'error' in result:
            _logger.error(f"Failed to send WhatsApp media: {result['error']}")
            raise UserError(_(f"Failed to send WhatsApp media: {result['error']}"))
        
        return result
    
    def mark_message_as_read(self, message_id):
        """Mark an incoming message as read"""
        message_data = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        endpoint = f"{self.phone_number_id}/messages"
        result = self._make_api_request(endpoint, method='POST', data=message_data)
        
        return 'error' not in result
    
    def get_media_url(self, media_id):
        """Get downloadable URL for media file"""
        result = self._make_api_request(media_id)
        
        if 'error' in result:
            _logger.error(f"Failed to get media URL: {result['error']}")
            return None
        
        return result.get('url')
    
    def download_media(self, media_url):
        """Download media file from WhatsApp"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
            }
            
            response = requests.get(media_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.content
            else:
                _logger.error(f"Failed to download media: {response.status_code}")
                return None
                
        except Exception as e:
            _logger.error(f"Media download error: {str(e)}")
            return None