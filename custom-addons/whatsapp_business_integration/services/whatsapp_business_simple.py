# -*- coding: utf-8 -*-

from odoo import api, models

class WhatsAppBusinessService(models.TransientModel):
    """WhatsApp Business API Service using Meta Graph API"""
    _name = 'whatsapp.business.service'
    _description = 'WhatsApp Business API Service'
    
    def test_method(self):
        """Temporary test method"""
        return True