#!/usr/bin/env python3
"""Test WhatsApp Service functionality"""

import odoorpc
import os

try:
    # Connect to Odoo
    print("Connecting to Odoo...")
    odoo = odoorpc.ODOO('localhost', port=8069)
    odoo.login('crm', 'admin', 'admin')
    print("✓ Connected to Odoo")

    # Test WhatsApp service
    try:
        whatsapp_service = odoo.env['whatsapp.business.service'].create({})
        print("✓ WhatsApp service created")
        
        # Test phone validation
        result = whatsapp_service.validate_phone_number('+905377178182')
        print(f"✓ Phone validation test: {result}")
        
        # Test API configuration properties
        print(f"✓ Base URL: {whatsapp_service.base_url}")
        print(f"✓ Phone Number: {whatsapp_service.phone_number}")
        print(f"✓ Business Account ID: {whatsapp_service.business_account_id}")
        print(f"✓ Phone Number ID: {whatsapp_service.phone_number_id}")
        print(f"✓ Access Token configured: {'Yes' if whatsapp_service.access_token else 'No'}")
        
    except Exception as e:
        print(f"✗ WhatsApp service error: {e}")
    
    # Test models
    try:
        message_model = odoo.env['whatsapp.message']
        conversation_model = odoo.env['whatsapp.conversation']
        print("✓ WhatsApp models accessible")
        
        # Count existing records
        message_count = message_model.search_count([])
        conversation_count = conversation_model.search_count([])
        print(f"✓ Messages: {message_count}, Conversations: {conversation_count}")
        
    except Exception as e:
        print(f"✗ Models error: {e}")
        
except Exception as e:
    print(f'Connection error: {e}')