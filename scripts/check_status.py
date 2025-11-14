#!/usr/bin/env python3
"""Check installed modules and fix meta_leads"""
import odoorpc

HOST = 'localhost'
PORT = 8069
DB = 'crm'
USER = 'admin'
PASSWORD = 'admin'

print("Connecting to Odoo...")
odoo = odoorpc.ODOO(HOST, port=PORT)
odoo.login(DB, USER, PASSWORD)
print("✓ Connected\n")

Module = odoo.env['ir.module.module']

# Check what's installed
print("Currently installed modules:")
installed = Module.search([('state', '=', 'installed')])
for mod_id in installed[:10]:  # Show first 10
    mod = Module.browse(mod_id)
    print(f"  {mod.name}")

print("\n" + "="*50)

# Check webhook modules
webhook_modules = ['meta_leads', 'webhooks_bridge', 'crm']
for mod_name in webhook_modules:
    mod_ids = Module.search([('name', '=', mod_name)])
    if mod_ids:
        mod = Module.browse(mod_ids[0])
        print(f"{mod_name}: {mod.state}")
    else:
        print(f"{mod_name}: NOT FOUND")

print("\n" + "="*50)
print("Webhook endpoints should be available at:")
print("- GET /webhooks/meta (verification)")
print("- POST /webhooks/meta (lead webhooks)")
print("- GET/POST /webhooks/google")

# Test if webhooks_bridge is working
try:
    # This will trigger a route compilation if module is loaded
    from odoo.addons.webhooks_bridge.controllers.webhooks import WebhooksController
    print("\n✓ Webhooks controller is accessible")
except Exception as e:
    print(f"\n⚠ Webhooks controller issue: {e}")