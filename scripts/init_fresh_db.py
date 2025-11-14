#!/usr/bin/env python3
import odoo
from odoo.tools import config

CONFIG_PATH = "/etc/odoo/odoo.conf"
DB_NAME = "crm"

# Load Odoo configuration
config.parse_config(["--config", CONFIG_PATH])

# Initialize the database with base module
print(f"Initializing database '{DB_NAME}'...")
odoo.service.db.exp_create_database(
    DB_NAME, 
    demo=False, 
    lang='en_US',
    user_password='admin'
)

print(f"✓ Database '{DB_NAME}' created successfully")

# Connect to the new database and set up admin
registry = odoo.registry(DB_NAME)
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    user = env.ref("base.user_admin")
    user.write({
        "login": "admin",
        "lang": "en_US",
        "password": "admin",
    })
    user.partner_id.write({
        "email": "admin@example.com",
        "phone": "+1-555-0100",
        "name": "Administrator",
        "country_id": env.ref("base.us").id,
    })
    cr.commit()
    print(f"✓ Admin user configured (login: admin, password: admin)")
