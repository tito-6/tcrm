# -*- coding: utf-8 -*-

import json
import logging
import hmac
import hashlib
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppWebhook(http.Controller):
    """WhatsApp Business API webhook controller"""
    
    @http.route('/whatsapp/webhook', type='http', auth='none', methods=['GET', 'POST'], csrf=False)
    def whatsapp_webhook(self, **kwargs):
        """Handle WhatsApp webhook requests"""
        
        if request.httprequest.method == 'GET':
            return self._verify_webhook(**kwargs)
        elif request.httprequest.method == 'POST':
            return self._process_webhook()
        else:
            return http.Response('Method not allowed', status=405)
    
    def _verify_webhook(self, **kwargs):
        """Verify webhook during setup"""
        try:
            # Get webhook verification parameters
            verify_token = kwargs.get('hub.verify_token')
            challenge = kwargs.get('hub.challenge')
            mode = kwargs.get('hub.mode')
            
            # Get configured verification token from environment or settings
            import os
            expected_token = os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN', 'your_verify_token_here')
            
            if mode == 'subscribe' and verify_token == expected_token:
                _logger.info("WhatsApp webhook verification successful")
                return http.Response(challenge, content_type='text/plain')
            else:
                _logger.warning(f"WhatsApp webhook verification failed: mode={mode}, token={verify_token}")
                return http.Response('Verification failed', status=403)
                
        except Exception as e:
            _logger.error(f"WhatsApp webhook verification error: {str(e)}")
            return http.Response('Verification error', status=500)
    
    def _process_webhook(self):
        """Process incoming webhook data"""
        try:
            # Get request data
            data = json.loads(request.httprequest.get_data(as_text=True))
            
            # Log incoming webhook for debugging
            _logger.info(f"Received WhatsApp webhook: {json.dumps(data, indent=2)}")
            
            # Verify webhook signature (optional but recommended)
            if not self._verify_signature(request.httprequest.get_data()):
                _logger.warning("WhatsApp webhook signature verification failed")
                return http.Response('Signature verification failed', status=403)
            
            # Process webhook entries
            for entry in data.get('entry', []):
                self._process_webhook_entry(entry)
            
            return http.Response('OK', content_type='text/plain')
            
        except json.JSONDecodeError as e:
            _logger.error(f"WhatsApp webhook JSON decode error: {str(e)}")
            return http.Response('Invalid JSON', status=400)
        except Exception as e:
            _logger.error(f"WhatsApp webhook processing error: {str(e)}")
            return http.Response('Processing error', status=500)
    
    def _verify_signature(self, payload):
        """Verify webhook signature from Meta"""
        try:
            import os
            app_secret = os.getenv('META_APP_SECRET')
            if not app_secret:
                _logger.warning("META_APP_SECRET not configured, skipping signature verification")
                return True  # Allow if not configured
            
            signature = request.httprequest.headers.get('X-Hub-Signature-256', '')
            if not signature:
                return False
            
            # Remove 'sha256=' prefix
            signature = signature.replace('sha256=', '')
            
            # Calculate expected signature
            expected_signature = hmac.new(
                app_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            _logger.error(f"Signature verification error: {str(e)}")
            return False
    
    def _process_webhook_entry(self, entry):
        """Process a single webhook entry"""
        try:
            # Get changes from the entry
            changes = entry.get('changes', [])
            
            for change in changes:
                field = change.get('field')
                value = change.get('value', {})
                
                if field == 'messages':
                    self._process_messages(value)
                elif field == 'message_deliveries':
                    self._process_delivery_status(value)
                elif field == 'message_reads':
                    self._process_read_status(value)
                else:
                    _logger.info(f"Unhandled webhook field: {field}")
                    
        except Exception as e:
            _logger.error(f"Webhook entry processing error: {str(e)}")
    
    def _process_messages(self, value):
        """Process incoming messages"""
        try:
            messages = value.get('messages', [])
            
            for message_data in messages:
                # Create message from webhook data
                WhatsAppMessage = request.env['whatsapp.message'].sudo()
                message = WhatsAppMessage.create_from_webhook({
                    'messages': [message_data],
                    'contacts': value.get('contacts', [])
                })
                
                if message:
                    _logger.info(f"Created message from webhook: {message.id}")
                    
                    # Auto-respond or trigger automation if needed
                    self._handle_incoming_message(message)
                else:
                    _logger.error("Failed to create message from webhook")
                    
        except Exception as e:
            _logger.error(f"Message processing error: {str(e)}")
    
    def _process_delivery_status(self, value):
        """Process message delivery status updates"""
        try:
            deliveries = value.get('deliveries', [])
            
            for delivery in deliveries:
                message_id = delivery.get('message_id')
                status = delivery.get('status')
                
                if message_id:
                    # Update message status
                    message = request.env['whatsapp.message'].sudo().search([
                        ('whatsapp_message_id', '=', message_id)
                    ], limit=1)
                    
                    if message:
                        message.status = status
                        _logger.info(f"Updated message {message_id} status to {status}")
                    
        except Exception as e:
            _logger.error(f"Delivery status processing error: {str(e)}")
    
    def _process_read_status(self, value):
        """Process message read status updates"""
        try:
            reads = value.get('reads', [])
            
            for read in reads:
                message_id = read.get('message_id')
                
                if message_id:
                    # Update message as read
                    message = request.env['whatsapp.message'].sudo().search([
                        ('whatsapp_message_id', '=', message_id)
                    ], limit=1)
                    
                    if message:
                        message.status = 'read'
                        _logger.info(f"Marked message {message_id} as read")
                    
        except Exception as e:
            _logger.error(f"Read status processing error: {str(e)}")
    
    def _handle_incoming_message(self, message):
        """Handle incoming message - auto-responses, notifications, etc."""
        try:
            # You can add custom logic here:
            # - Auto-responses based on keywords
            # - Notifications to users
            # - Integration with other systems
            # - Lead scoring updates
            
            # Example: Send notification to assigned user
            if message.lead_id and message.lead_id.user_id:
                # Create internal note or send email notification
                message.lead_id.message_post(
                    body=f"New WhatsApp message received: {message.preview}",
                    subject="New WhatsApp Message",
                    subtype_xmlid="mail.mt_note"
                )
            
        except Exception as e:
            _logger.error(f"Incoming message handling error: {str(e)}")