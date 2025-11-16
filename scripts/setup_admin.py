import odoo
from odoo.tools import config

CONFIG_PATH = "/etc/odoo/odoo.conf"
DB_NAME = "crm"

# Load Odoo configuration so we connect using the same settings as the running server.
config.parse_config(["--config", CONFIG_PATH])

registry = odoo.registry(DB_NAME)
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    user = env.ref("base.user_admin")
    user.write({
        "login": "queenvilla",
        "lang": "en_US",
        "password": "QueenVilla2025!@#Strong",
    })
    # Update related partner info for completeness.
    user.partner_id.write({
        "email": "admin@queenvilla.com",
        "phone": "+90-555-0100",
        "country_id": env.ref("base.tr").id,
    })
    cr.commit()
    print(f"Updated administrator (ID {user.id}) with login 'queenvilla'.")
