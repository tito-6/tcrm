# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class WhatsAppConversation(models.Model):
    """WhatsApp conversation model to group messages by contact"""
    _name = 'whatsapp.conversation'
    _description = 'WhatsApp Conversation'
    _order = 'last_message_date desc'
    _rec_name = 'display_name'
    
    # Basic info
    phone_number = fields.Char(
        string='Phone Number',
        required=True,
        help='WhatsApp phone number (international format without +)'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    # Relations
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        help='Related contact'
    )
    
    lead_id = fields.Many2one(
        'crm.lead',
        string='Lead',
        help='Related CRM lead'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Assigned To',
        help='User responsible for this conversation'
    )
    
    # Conversation stats
    message_count = fields.Integer(
        string='Message Count',
        default=0
    )
    
    unread_count = fields.Integer(
        string='Unread Messages',
        compute='_compute_unread_count',
        search='_search_unread_count'
    )
    
    last_message_date = fields.Datetime(
        string='Last Message',
        help='Timestamp of the last message in this conversation'
    )
    
    last_message_preview = fields.Char(
        string='Last Message Preview',
        compute='_compute_last_message_preview'
    )
    
    # Status
    status = fields.Selection([
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('blocked', 'Blocked'),
    ], string='Status', default='active')
    
    # Messages
    message_ids = fields.One2many(
        'whatsapp.message',
        'conversation_id',
        string='Messages'
    )
    
    @api.depends('partner_id', 'phone_number')
    def _compute_display_name(self):
        """Compute display name for conversation"""
        for conversation in self:
            if conversation.partner_id:
                name = conversation.partner_id.name
            else:
                name = f"WhatsApp {conversation.phone_number}"
            
            conversation.display_name = name
    
    @api.depends('message_ids.status', 'message_ids.direction')
    def _compute_unread_count(self):
        """Compute number of unread incoming messages"""
        for conversation in self:
            unread_count = self.env['whatsapp.message'].search_count([
                ('conversation_id', '=', conversation.id),
                ('direction', '=', 'incoming'),
                ('status', 'in', ['delivered', 'sent'])  # Not read yet
            ])
            conversation.unread_count = unread_count
    
    def _search_unread_count(self, operator, value):
        """Search method for unread_count computed field"""
        conversations = self.search([])
        conversations._compute_unread_count()
        
        matching_ids = []
        for conversation in conversations:
            if operator == '>' and conversation.unread_count > value:
                matching_ids.append(conversation.id)
            elif operator == '=' and conversation.unread_count == value:
                matching_ids.append(conversation.id)
            elif operator == '<' and conversation.unread_count < value:
                matching_ids.append(conversation.id)
            elif operator == '!=' and conversation.unread_count != value:
                matching_ids.append(conversation.id)
        
        return [('id', 'in', matching_ids)]
    
    @api.depends('message_ids')
    def _compute_last_message_preview(self):
        """Compute preview of last message"""
        for conversation in self:
            last_message = conversation.message_ids.sorted('create_date', reverse=True)[:1]
            if last_message:
                conversation.last_message_preview = last_message.preview
            else:
                conversation.last_message_preview = _("No messages yet")
    
    @api.model
    def find_or_create_conversation(self, phone_number):
        """Find existing conversation or create new one"""
        # First try to find existing conversation
        conversation = self.search([
            ('phone_number', '=', phone_number)
        ], limit=1)
        
        if conversation:
            return conversation
        
        # Try to find related contact
        partner = self.env['res.partner'].search([
            ('mobile', 'ilike', phone_number.replace('+', ''))
        ], limit=1)
        
        if not partner:
            partner = self.env['res.partner'].search([
                ('phone', 'ilike', phone_number.replace('+', ''))
            ], limit=1)
        
        # Try to find related lead
        lead = self.env['crm.lead'].search([
            ('mobile', 'ilike', phone_number.replace('+', ''))
        ], limit=1)
        
        if not lead:
            lead = self.env['crm.lead'].search([
                ('phone', 'ilike', phone_number.replace('+', ''))
            ], limit=1)
        
        # Create new conversation
        conversation_vals = {
            'phone_number': phone_number,
            'partner_id': partner.id if partner else False,
            'lead_id': lead.id if lead else False,
            'status': 'active',
        }
        
        conversation = self.create(conversation_vals)
        return conversation
    
    def send_text_message(self, message_text):
        """Send a text message in this conversation"""
        message_vals = {
            'conversation_id': self.id,
            'direction': 'outgoing',
            'message_type': 'text',
            'body': message_text,
            'user_id': self.env.user.id,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'lead_id': self.lead_id.id if self.lead_id else False,
        }
        
        message = self.env['whatsapp.message'].create(message_vals)
        message.send_message()
        
        # Update conversation stats
        self.message_count += 1
        self.last_message_date = datetime.now()
        
        return message
    
    def send_template_message(self, template_name, language_code='en', parameters=None):
        """Send a template message in this conversation"""
        message_vals = {
            'conversation_id': self.id,
            'direction': 'outgoing',
            'message_type': 'template',
            'template_name': template_name,
            'template_language': language_code,
            'template_parameters': str(parameters) if parameters else '',
            'user_id': self.env.user.id,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'lead_id': self.lead_id.id if self.lead_id else False,
        }
        
        message = self.env['whatsapp.message'].create(message_vals)
        message.send_message()
        
        # Update conversation stats
        self.message_count += 1
        self.last_message_date = datetime.now()
        
        return message
    
    def mark_all_as_read(self):
        """Mark all incoming messages as read"""
        incoming_messages = self.message_ids.filtered(
            lambda m: m.direction == 'incoming' and m.status in ['delivered', 'sent']
        )
        
        for message in incoming_messages:
            message.mark_as_read()
            message.status = 'read'
    
    def archive_conversation(self):
        """Archive this conversation"""
        self.status = 'archived'
    
    def unarchive_conversation(self):
        """Unarchive this conversation"""
        self.status = 'active'
    
    def action_open_messages(self):
        """Open messages view for this conversation"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('WhatsApp Messages'),
            'res_model': 'whatsapp.message',
            'view_mode': 'tree,form',
            'domain': [('conversation_id', '=', self.id)],
            'context': {
                'default_conversation_id': self.id,
                'default_direction': 'outgoing',
                'default_message_type': 'text',
            },
        }
    
    def action_send_message(self):
        """Open wizard to send new message"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send WhatsApp Message'),
            'res_model': 'whatsapp.message.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_conversation_id': self.id,
                'default_phone_number': self.phone_number,
            },
        }