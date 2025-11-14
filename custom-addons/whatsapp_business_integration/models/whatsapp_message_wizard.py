# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class WhatsAppMessageWizard(models.TransientModel):
    """Wizard for sending WhatsApp messages"""
    _name = 'whatsapp.message.wizard'
    _description = 'Send WhatsApp Message'
    
    # Target info
    conversation_id = fields.Many2one(
        'whatsapp.conversation',
        string='Conversation',
        required=True
    )
    
    phone_number = fields.Char(
        string='Phone Number',
        required=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact'
    )
    
    lead_id = fields.Many2one(
        'crm.lead',
        string='Lead'
    )
    
    # Message content
    message_type = fields.Selection([
        ('text', 'Text Message'),
        ('template', 'Template Message'),
    ], string='Message Type', default='text', required=True)
    
    message_body = fields.Text(
        string='Message',
        help='Text message content'
    )
    
    # Template fields
    template_name = fields.Selection(
        selection='_get_template_options',
        string='Template'
    )
    
    template_language = fields.Selection([
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('pt', 'Portuguese'),
    ], string='Language', default='en')
    
    template_parameters = fields.Text(
        string='Template Parameters',
        help='Comma-separated parameters for template (if needed)'
    )
    
    def _get_template_options(self):
        """Get available WhatsApp message templates"""
        # This would be populated from Meta API
        # For now, return common template examples
        return [
            ('hello_world', 'Hello World'),
            ('appointment_reminder', 'Appointment Reminder'),
            ('order_confirmation', 'Order Confirmation'),
            ('welcome_message', 'Welcome Message'),
        ]
    
    @api.onchange('message_type')
    def _onchange_message_type(self):
        """Clear fields when message type changes"""
        if self.message_type == 'text':
            self.template_name = False
            self.template_parameters = False
        elif self.message_type == 'template':
            self.message_body = False
    
    def action_send_message(self):
        """Send the WhatsApp message"""
        if not self.conversation_id:
            raise UserError(_("No conversation selected"))
        
        if self.message_type == 'text':
            if not self.message_body:
                raise UserError(_("Message content is required"))
            
            message = self.conversation_id.send_text_message(self.message_body)
            
        elif self.message_type == 'template':
            if not self.template_name:
                raise UserError(_("Template selection is required"))
            
            # Parse parameters
            parameters = []
            if self.template_parameters:
                parameters = [p.strip() for p in self.template_parameters.split(',')]
            
            message = self.conversation_id.send_template_message(
                self.template_name,
                self.template_language,
                parameters
            )
        
        # Show success message
        if message and message.status != 'failed':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Message Sent'),
                    'message': _('WhatsApp message has been sent successfully.'),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Send Failed'),
                    'message': _('Failed to send WhatsApp message. Please check the error log.'),
                    'type': 'warning',
                }
            }
    
    def action_send_and_close(self):
        """Send message and close wizard"""
        self.action_send_message()
        return {'type': 'ir.actions.act_window_close'}