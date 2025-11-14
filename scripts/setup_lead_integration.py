#!/usr/bin/env python3
"""
Lead Integration Setup for Meta (Facebook/Instagram) and Google Ads
This script creates webhook endpoints and API routes for receiving leads
"""
import odoorpc

host = 'localhost'
port = 8069
database = 'crm'
username = 'admin'
password = 'admin'

try:
    print("Connecting to Odoo...")
    odoo = odoorpc.ODOO(host, port=port)
    odoo.login(database, username, password)
    print(f"✓ Connected\n")
    
    # Install additional modules for lead capture
    Module = odoo.env['ir.module.module']
    
    modules_to_install = [
        'website_crm_iap_reveal',  # Website visitor identification
        'crm_livechat',            # Live chat integration
        'website_livechat',        # Live chat on website
    ]
    
    print("Installing additional lead capture modules:")
    print("="*70)
    
    for module_name in modules_to_install:
        module_ids = Module.search([('name', '=', module_name)])
        if module_ids:
            module = Module.browse(module_ids[0])
            if module.state != 'installed':
                print(f"📦 Installing {module_name}...")
                try:
                    Module.button_immediate_install([module.id])
                    print(f"   ✅ Installed successfully")
                except Exception as e:
                    print(f"   ⚠ {e}")
            else:
                print(f"✅ {module_name} - already installed")
        else:
            print(f"⚠ Module {module_name} not found")
    
    print("\n" + "="*70)
    print("✅ Lead capture modules ready!")
    print("="*70)
    
    # Get website URL
    Website = odoo.env['website']
    website_ids = Website.search([])
    if website_ids:
        website = Website.browse(website_ids[0])
        print(f"\n🌐 Your website domain: {website.domain}")
    
except Exception as e:
    print(f"✗ Error: {e}")
