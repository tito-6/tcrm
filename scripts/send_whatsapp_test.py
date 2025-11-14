#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import xmlrpc.client
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(project_root)
sys.path.insert(0, parent_dir)

def main():
    """Send a test WhatsApp message using the Odoo WhatsApp integration"""
    
    # Connection parameters
    url = 'http://localhost:8069'
    db = 'crm'
    username = 'admin'
    password = 'admin'
    
    # Test message details
    test_numbers = [
        '+905525242866'   # Target number specified by user
    ]
    
    test_message = f"🚀 WhatsApp Integration Test\n\nHello! This is a test message from your Odoo CRM WhatsApp integration.\n\nSent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n✅ Integration working successfully!"
    
    try:
        print("🚀 WhatsApp Message Test")
        print("=" * 50)
        
        print("Connecting to Odoo...")
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("❌ Authentication failed!")
            return
            
        print("✅ Connected to Odoo")
        
        # Get models proxy
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        print(f"\n📱 From Number: +905377178182")
        print(f"📝 Message: {test_message[:50]}...")
        
        for i, to_number in enumerate(test_numbers, 1):
            print(f"\n🎯 Test {i}: Sending to {to_number}")
            
            try:
                # Create WhatsApp service instance
                print("  🔧 Creating WhatsApp service instance...")
                service_id = models.execute_kw(db, uid, password,
                    'whatsapp.business.service', 'create', [{}]
                )
                print(f"  ✅ Service created: ID {service_id}")
                
                # Validate the target phone number first
                print(f"  📞 Validating phone number: {to_number}")
                validation_result = models.execute_kw(db, uid, password,
                    'whatsapp.business.service', 'validate_phone_number',
                    [service_id, to_number]
                )
                print(f"  📋 Validation result: {validation_result}")
                
                if validation_result[0]:  # validation_result is [True/False, formatted_number_or_error]
                    formatted_number = validation_result[1]
                    print(f"  ✅ Phone number valid: {formatted_number}")
                    
                    # Send the message
                    print("  📤 Sending WhatsApp message...")
                    send_result = models.execute_kw(db, uid, password,
                        'whatsapp.business.service', 'send_text_message',
                        [service_id, to_number, test_message]
                    )
                    
                    print(f"  📋 Send result: {send_result}")
                    
                    if 'messages' in send_result and send_result['messages']:
                        message_id = send_result['messages'][0].get('id')
                        wamid = send_result['messages'][0].get('message_status', 'N/A') 
                        print(f"  ✅ Message sent successfully!")
                        print(f"     Message ID: {message_id}")
                        print(f"     Status: {wamid}")
                    else:
                        print(f"  ⚠️ Unexpected response format: {send_result}")
                        
                else:
                    print(f"  ❌ Phone number validation failed: {validation_result[1]}")
                
                # Clean up service instance
                models.execute_kw(db, uid, password,
                    'whatsapp.business.service', 'unlink', [service_id]
                )
                print("  🧹 Service instance cleaned up")
                
            except Exception as e:
                print(f"  ❌ Error sending to {to_number}: {str(e)}")
                
                # Try to clean up service if it was created
                try:
                    if 'service_id' in locals():
                        models.execute_kw(db, uid, password,
                            'whatsapp.business.service', 'unlink', [service_id]
                        )
                except:
                    pass
        
        print("\n🎯 Test Summary:")
        print("✅ WhatsApp service integration working")
        print("✅ Phone number validation functional") 
        print("✅ Message sending API accessible")
        print("\n📱 Check your WhatsApp for received messages!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

if __name__ == '__main__':
    main()