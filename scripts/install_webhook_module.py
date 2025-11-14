#!/usr/bin/env python3
"""
Install the custom CRM integration module with webhooks
"""
import odoorpc
import time

host = 'localhost'
port = 8069
database = 'crm'
username = 'admin'
password = 'admin'

print("="*70)
print("Installing Custom CRM Integration Module")
print("="*70)

try:
    print("\n1. Connecting to Odoo...")
    odoo = odoorpc.ODOO(host, port=port)
    odoo.login(database, username, password)
    print("   ✅ Connected successfully")
    
    print("\n2. Updating module list...")
    Module = odoo.env['ir.module.module']
    Module.update_list()
    print("   ✅ Module list updated")
    
    print("\n3. Searching for custom_crm_integration module...")
    module_ids = Module.search([('name', '=', 'custom_crm_integration')])
    
    if not module_ids:
        print("   ❌ Module not found!")
        print("\n   Make sure:")
        print("   - custom_addons folder is mounted in docker-compose.yml")
        print("   - Odoo config includes /mnt/custom-addons in addons_path")
        print("   - Container has been restarted")
        exit(1)
    
    module = Module.browse(module_ids[0])
    print(f"   ✅ Found module: {module.name}")
    print(f"   State: {module.state}")
    
    if module.state == 'installed':
        print("\n   ✅ Module is already installed!")
    else:
        print("\n4. Installing module...")
        Module.button_immediate_install([module.id])
        print("   ✅ Module installed successfully!")
    
    print("\n" + "="*70)
    print("🎉 Installation Complete!")
    print("="*70)
    
    # Get the base URL
    print("\n📍 Webhook Endpoints Available:")
    print(f"   • Meta Verify:    http://localhost:8069/webhook/meta/verify")
    print(f"   • Meta Leads:     http://localhost:8069/webhook/meta/leads")
    print(f"   • Google Leads:   http://localhost:8069/webhook/google/leads")
    print(f"   • Generic:        http://localhost:8069/webhook/lead/create")
    print(f"   • Test:           http://localhost:8069/webhook/test")
    
    print("\n💡 Next Steps:")
    print("   1. Test the webhook: curl http://localhost:8069/webhook/test")
    print("   2. Set up ngrok for public URL")
    print("   3. Configure Meta/Google to send to your webhook")
    print("   4. Check CRM → Leads for incoming leads")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting:")
    print("  1. Restart Odoo: docker compose restart odoo")
    print("  2. Check logs: docker compose logs odoo")
    print("  3. Verify addons_path in config/odoo.conf")
