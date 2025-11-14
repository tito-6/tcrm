#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import xmlrpc.client

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(project_root)
sys.path.insert(0, parent_dir)

def main():
    """Test direct model access through XML-RPC"""
    
    # Connection parameters
    url = 'http://localhost:8069'
    db = 'crm'
    username = 'admin'
    password = 'admin'
    
    try:
        print("🚀 Testing WhatsApp Model Direct Access")
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
        
        # Test direct model operations
        whatsapp_models = [
            'whatsapp.message',
            'whatsapp.conversation', 
            'whatsapp.business.service',
            'whatsapp.message.wizard'
        ]
        
        print("\n🧪 Testing Direct Model Access:")
        
        for model_name in whatsapp_models:
            try:
                print(f"\n📋 Testing {model_name}:")
                
                # Try to search (should work if security allows)
                result = models.execute_kw(db, uid, password,
                    model_name, 'search',
                    [[]],
                    {'limit': 5}
                )
                
                print(f"  ✅ Search successful: Found {len(result)} records")
                
                # Try to create a test record (if applicable)
                if model_name == 'whatsapp.business.service':
                    print("  🧪 Testing service creation...")
                    try:
                        service_id = models.execute_kw(db, uid, password,
                            model_name, 'create',
                            [{}]
                        )
                        print(f"  ✅ Service created with ID: {service_id}")
                        
                        # Test a method call
                        print("  🧪 Testing method call...")
                        try:
                            result = models.execute_kw(db, uid, password,
                                model_name, 'validate_phone_number',
                                [service_id, '+905377178182']
                            )
                            print(f"  ✅ Method call successful: {result}")
                        except Exception as e:
                            print(f"  ⚠️ Method call failed: {str(e)}")
                            
                        # Clean up
                        models.execute_kw(db, uid, password,
                            model_name, 'unlink',
                            [service_id]
                        )
                        print("  🧹 Test record cleaned up")
                        
                    except Exception as e:
                        print(f"  ⚠️ Service creation failed: {str(e)}")
                
            except Exception as e:
                print(f"  ❌ Access denied: {str(e)}")
                
        print("\n🎯 Testing WhatsApp Service Methods:")
        try:
            # Create service instance
            service_id = models.execute_kw(db, uid, password,
                'whatsapp.business.service', 'create', [{}]
            )
            
            # Test phone validation
            print("📱 Testing phone validation...")
            result = models.execute_kw(db, uid, password,
                'whatsapp.business.service', 'validate_phone_number',
                [service_id, '+905377178182']
            )
            print(f"  Phone validation result: {result}")
            
            # Clean up
            models.execute_kw(db, uid, password,
                'whatsapp.business.service', 'unlink', [service_id]
            )
            
        except Exception as e:
            print(f"  ❌ Service method test failed: {str(e)}")
            
        print("\n✅ Direct access test completed!")
    
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")

if __name__ == '__main__':
    main()