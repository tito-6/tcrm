# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class CrmLead(models.Model):
    """Extend CRM lead model with WhatsApp functionality"""
    _inherit = 'crm.lead'
    
    # WhatsApp fields
    whatsapp_number = fields.Char(
        string='WhatsApp Number',
        help='WhatsApp phone number for this lead'
    )
    
    has_whatsapp = fields.Boolean(
        string='Has WhatsApp',
        compute='_compute_has_whatsapp',
        store=True,
        help='Whether this lead has WhatsApp available'
    )
    
    # Conversation relation
    whatsapp_conversation_ids = fields.One2many(
        'whatsapp.conversation',
        'lead_id',
        string='WhatsApp Conversations'
    )
    
    whatsapp_conversation_count = fields.Integer(
        string='WhatsApp Conversations',
        compute='_compute_whatsapp_conversation_count'
    )
    
    whatsapp_message_count = fields.Integer(
        string='WhatsApp Messages',
        compute='_compute_whatsapp_message_count'
    )
    
    last_whatsapp_message_date = fields.Datetime(
        string='Last WhatsApp Message',
        compute='_compute_last_whatsapp_message_date'
    )
    
    @api.depends('whatsapp_number', 'mobile', 'phone')
    def _compute_has_whatsapp(self):
        """Compute if lead has WhatsApp available"""
        for lead in self:
            lead.has_whatsapp = bool(
                lead.whatsapp_number or 
                lead.mobile or 
                lead.phone
            )
    
    @api.depends('whatsapp_conversation_ids')
    def _compute_whatsapp_conversation_count(self):
        """Compute number of WhatsApp conversations"""
        for lead in self:
            lead.whatsapp_conversation_count = len(lead.whatsapp_conversation_ids)
    
    @api.depends('whatsapp_conversation_ids.message_ids')
    def _compute_whatsapp_message_count(self):
        """Compute total number of WhatsApp messages"""
        for lead in self:
            message_count = sum(
                len(conv.message_ids) for conv in lead.whatsapp_conversation_ids
            )
            lead.whatsapp_message_count = message_count
    
    @api.depends('whatsapp_conversation_ids.last_message_date')
    def _compute_last_whatsapp_message_date(self):
        """Compute last WhatsApp message date"""
        for lead in self:
            if lead.whatsapp_conversation_ids:
                last_conversation = lead.whatsapp_conversation_ids.sorted(
                    'last_message_date', reverse=True
                )[:1]
                lead.last_whatsapp_message_date = last_conversation.last_message_date
            else:
                lead.last_whatsapp_message_date = False
    
    def get_whatsapp_phone_number(self):
        """Get the best WhatsApp phone number for this lead"""
        if self.whatsapp_number:
            return self.whatsapp_number
        elif self.mobile:
            return self.mobile
        elif self.phone:
            return self.phone
        else:
            return False
    
    def action_send_whatsapp_message(self):
        """Open WhatsApp message wizard"""
        phone_number = self.get_whatsapp_phone_number()
        if not phone_number:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Phone Number'),
                    'message': _('This lead has no phone number configured for WhatsApp.'),
                    'type': 'warning',
                }
            }
        
        # Find or create conversation
        conversation = self.env['whatsapp.conversation'].find_or_create_conversation(phone_number)
        
        # Link conversation to lead if not already linked
        if not conversation.lead_id:
            conversation.lead_id = self.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send WhatsApp Message'),
            'res_model': 'whatsapp.message.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_conversation_id': conversation.id,
                'default_phone_number': phone_number,
                'default_lead_id': self.id,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
            },
        }
    
    def action_view_whatsapp_conversations(self):
        """View WhatsApp conversations for this lead"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('WhatsApp Conversations'),
            'res_model': 'whatsapp.conversation',
            'view_mode': 'tree,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {
                'default_lead_id': self.id,
            },
        }
    
    def action_view_whatsapp_messages(self):
        """View all WhatsApp messages for this lead"""
        conversation_ids = self.whatsapp_conversation_ids.ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('WhatsApp Messages'),
            'res_model': 'whatsapp.message',
            'view_mode': 'tree,form',
            'domain': [('conversation_id', 'in', conversation_ids)],
            'context': {
                'default_lead_id': self.id,
            },
        }
    
    def send_whatsapp_welcome_message(self):
        """Send a welcome WhatsApp message to new leads"""
        phone_number = self.get_whatsapp_phone_number()
        if not phone_number:
            return False
        
        # Find or create conversation
        conversation = self.env['whatsapp.conversation'].find_or_create_conversation(phone_number)
        
        # Link conversation to lead
        if not conversation.lead_id:
            conversation.lead_id = self.id
        
        # Send welcome message
        welcome_text = f"""Hello {self.contact_name or 'there'}!
        
Thank you for your interest in our services. We've received your inquiry and will get back to you shortly.

Best regards,
{self.user_id.name if self.user_id else 'Our Team'}"""
        
        return conversation.send_text_message(welcome_text)