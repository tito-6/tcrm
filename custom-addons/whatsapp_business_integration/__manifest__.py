# -*- coding: utf-8 -*-
{
    'name': 'WhatsApp Business Integration',
    'version': '18.0.1.0.0',
    'category': 'CRM',
    'summary': 'WhatsApp Business API Integration for CRM',
    'description': '''
WhatsApp Business Integration
=============================

This module provides WhatsApp Business API integration for Odoo CRM using Meta's 
WhatsApp Business API. Features include:

* Send WhatsApp messages from CRM leads and contacts
* Receive and track WhatsApp messages 
* Message templates and quick actions
* Delivery status tracking
* Media file support (images, documents, etc.)
* Integration with existing Meta app credentials
* Webhook processing for real-time updates

Requirements:
* Meta WhatsApp Business API access
* Valid WhatsApp Business Account
* Meta app with WhatsApp permissions
    ''',
    'author': 'Custom Development Team',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'crm',
        'mail',
        'contacts',
        'custom_crm_integration',  # Our existing Meta integration
    ],
    'data': [
        'security/whatsapp_groups.xml',
        'security/ir.model.access.csv',
        'data/whatsapp_message_templates.xml',
        'views/whatsapp_message_views.xml',
        'views/whatsapp_conversation_views.xml',
        'views/res_partner_views.xml',
        'views/crm_lead_views.xml',
        'views/whatsapp_menu_views.xml',
        'views/whatsapp_message_wizard_views.xml',
    ],
    'demo': [
        # Demo data if needed
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'external_dependencies': {
        'python': ['requests', 'phonenumbers'],
    },
}