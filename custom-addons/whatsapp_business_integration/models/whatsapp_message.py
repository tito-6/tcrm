# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class WhatsAppMessage(models.Model):
    """WhatsApp message model to track all messages"""
    _name = 'whatsapp.message'
    _description = 'WhatsApp Message'
    _order = 'create_date desc'
    _rec_name = 'preview'
    
    # Basic message info
    whatsapp_message_id = fields.Char(
        string='WhatsApp Message ID',
        help='Unique message ID from WhatsApp API'
    )
    
    conversation_id = fields.Many2one(
        'whatsapp.conversation',
        string='Conversation',
        required=True,
        ondelete='cascade'
    )
    
    # Message content
    message_type = fields.Selection([
        ('text', 'Text'),
        ('image', 'Image'),
        ('document', 'Document'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('template', 'Template'),
        ('interactive', 'Interactive'),
        ('location', 'Location'),
        ('contacts', 'Contacts'),
    ], string='Message Type', default='text', required=True)
    
    direction = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
    ], string='Direction', required=True)
    
    body = fields.Text(string='Message Body')
    
    # Media fields
    media_url = fields.Char(string='Media URL')
    media_mime_type = fields.Char(string='Media MIME Type')
    media_filename = fields.Char(string='Media Filename')
    media_caption = fields.Text(string='Media Caption')
    media_id = fields.Char(string='WhatsApp Media ID')
    
    # Template fields
    template_name = fields.Char(string='Template Name')
    template_language = fields.Char(string='Template Language')
    template_parameters = fields.Text(string='Template Parameters')
    
    # Status tracking
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    ], string='Status', default='pending')
    
    error_message = fields.Text(string='Error Message')
    
    # Timestamps
    timestamp = fields.Datetime(
        string='Message Timestamp',
        help='Original timestamp from WhatsApp'
    )
    
    # Relations
    lead_id = fields.Many2one(
        'crm.lead',
        string='Related Lead',
        help='CRM Lead associated with this message'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        help='Contact associated with this message'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Sent By',
        help='User who sent the message (for outgoing messages)'
    )
    
    # Computed fields
    preview = fields.Char(
        string='Preview',
        compute='_compute_preview',
        store=True
    )
    
    phone_number = fields.Char(
        related='conversation_id.phone_number',
        string='Phone Number',
        store=True
    )
    
    @api.depends('message_type', 'body', 'template_name', 'media_filename')
    def _compute_preview(self):
        """Compute message preview for display"""
        for message in self:
            if message.message_type == 'text':
                preview = message.body[:50] if message.body else 'Text message'
            elif message.message_type == 'template':
                preview = f"Template: {message.template_name or 'Unknown'}"
            elif message.message_type in ['image', 'document', 'audio', 'video']:
                filename = message.media_filename or 'media file'
                preview = f"{message.message_type.title()}: {filename}"
            else:
                preview = f"{message.message_type.title()} message"
            
            message.preview = preview
    
    def send_message(self):
        """Send this message via WhatsApp Business API"""
        whatsapp_service = self.env['whatsapp.business.service']
        
        try:
            if self.message_type == 'text':
                result = whatsapp_service.send_text_message(
                    self.conversation_id.phone_number,
                    self.body
                )
            elif self.message_type == 'template':
                # Parse template parameters
                parameters = []
                if self.template_parameters:
                    try:
                        import json
                        parameters = json.loads(self.template_parameters)
                    except:
                        parameters = self.template_parameters.split(',')
                
                result = whatsapp_service.send_template_message(
                    self.conversation_id.phone_number,
                    self.template_name,
                    self.template_language or 'en',
                    parameters
                )
            elif self.message_type in ['image', 'document', 'audio', 'video']:
                result = whatsapp_service.send_media_message(
                    self.conversation_id.phone_number,
                    self.message_type,
                    self.media_url,
                    self.media_caption
                )
            else:
                raise Exception(f"Unsupported message type: {self.message_type}")
            
            # Update message with WhatsApp response
            if result and 'messages' in result:
                message_info = result['messages'][0]
                self.whatsapp_message_id = message_info.get('id')
                self.status = 'sent'
            else:
                self.status = 'failed'
                self.error_message = str(result)
                
        except Exception as e:
            _logger.error(f"Failed to send WhatsApp message: {str(e)}")
            self.status = 'failed'
            self.error_message = str(e)
    
    def mark_as_read(self):
        """Mark incoming message as read"""
        if self.direction == 'incoming' and self.whatsapp_message_id:
            whatsapp_service = self.env['whatsapp.business.service']
            whatsapp_service.mark_message_as_read(self.whatsapp_message_id)
    
    @api.model
    def create_from_webhook(self, webhook_data):
        """Create message from webhook data"""
        try:
            # Extract message data from webhook
            message_data = webhook_data.get('messages', [{}])[0]
            contact_data = webhook_data.get('contacts', [{}])[0]
            
            phone_number = contact_data.get('wa_id', '')
            
            # Find or create conversation
            conversation = self.env['whatsapp.conversation'].find_or_create_conversation(
                phone_number
            )
            
            # Create message
            message_vals = {
                'whatsapp_message_id': message_data.get('id'),
                'conversation_id': conversation.id,
                'direction': 'incoming',
                'message_type': message_data.get('type', 'text'),
                'timestamp': datetime.fromtimestamp(int(message_data.get('timestamp', 0))),
                'status': 'delivered',
            }
            
            # Handle different message types
            if message_vals['message_type'] == 'text':
                message_vals['body'] = message_data.get('text', {}).get('body', '')
            elif message_vals['message_type'] in ['image', 'document', 'audio', 'video']:
                media_data = message_data.get(message_vals['message_type'], {})
                message_vals.update({
                    'media_id': media_data.get('id'),
                    'media_mime_type': media_data.get('mime_type'),
                    'media_filename': media_data.get('filename'),
                    'media_caption': media_data.get('caption'),
                })
            
            # Set relations
            message_vals['partner_id'] = conversation.partner_id.id if conversation.partner_id else False
            message_vals['lead_id'] = conversation.lead_id.id if conversation.lead_id else False
            
            message = self.create(message_vals)
            
            # Update conversation
            conversation.last_message_date = message.timestamp
            conversation.message_count += 1
            
            return message
            
        except Exception as e:
            _logger.error(f"Failed to create message from webhook: {str(e)}")
            return False
    
    def action_open_conversation(self):
        """Open the conversation this message belongs to"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('WhatsApp Conversation'),
            'res_model': 'whatsapp.conversation',
            'res_id': self.conversation_id.id,
            'view_mode': 'form',
            'target': 'current',
        }