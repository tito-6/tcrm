# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ResPartner(models.Model):
    """Extend partner model with WhatsApp functionality"""
    _inherit = 'res.partner'
    
    # WhatsApp fields
    whatsapp_number = fields.Char(
        string='WhatsApp Number',
        help='WhatsApp phone number for this contact'
    )
    
    has_whatsapp = fields.Boolean(
        string='Has WhatsApp',
        compute='_compute_has_whatsapp',
        store=True,
        help='Whether this contact has WhatsApp available'
    )
    
    # Conversation relation
    whatsapp_conversation_ids = fields.One2many(
        'whatsapp.conversation',
        'partner_id',
        string='WhatsApp Conversations'
    )
    
    whatsapp_conversation_count = fields.Integer(
        string='WhatsApp Conversations',
        compute='_compute_whatsapp_conversation_count'
    )
    
    last_whatsapp_message_date = fields.Datetime(
        string='Last WhatsApp Message',
        compute='_compute_last_whatsapp_message_date'
    )
    
    @api.depends('whatsapp_number', 'mobile', 'phone')
    def _compute_has_whatsapp(self):
        """Compute if contact has WhatsApp available"""
        for partner in self:
            partner.has_whatsapp = bool(
                partner.whatsapp_number or 
                partner.mobile or 
                partner.phone
            )
    
    @api.depends('whatsapp_conversation_ids')
    def _compute_whatsapp_conversation_count(self):
        """Compute number of WhatsApp conversations"""
        for partner in self:
            partner.whatsapp_conversation_count = len(partner.whatsapp_conversation_ids)
    
    @api.depends('whatsapp_conversation_ids.last_message_date')
    def _compute_last_whatsapp_message_date(self):
        """Compute last WhatsApp message date"""
        for partner in self:
            if partner.whatsapp_conversation_ids:
                last_conversation = partner.whatsapp_conversation_ids.sorted(
                    'last_message_date', reverse=True
                )[:1]
                partner.last_whatsapp_message_date = last_conversation.last_message_date
            else:
                partner.last_whatsapp_message_date = False
    
    def get_whatsapp_phone_number(self):
        """Get the best WhatsApp phone number for this contact"""
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
                    'message': _('This contact has no phone number configured for WhatsApp.'),
                    'type': 'warning',
                }
            }
        
        # Find or create conversation
        conversation = self.env['whatsapp.conversation'].find_or_create_conversation(phone_number)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send WhatsApp Message'),
            'res_model': 'whatsapp.message.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_conversation_id': conversation.id,
                'default_phone_number': phone_number,
                'default_partner_id': self.id,
            },
        }
    
    def action_view_whatsapp_conversations(self):
        """View WhatsApp conversations for this contact"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('WhatsApp Conversations'),
            'res_model': 'whatsapp.conversation',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
            },
        }
    
    def action_view_whatsapp_messages(self):
        """View all WhatsApp messages for this contact"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('WhatsApp Messages'),
            'res_model': 'whatsapp.message',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
            },
        }