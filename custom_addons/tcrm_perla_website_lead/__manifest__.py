# -*- coding: utf-8 -*-
{
    'name': 'TCRM Perla Website Lead',
    'version': '19.0.1.0.0',
    'category': 'CRM',
    'summary': 'Signed public webhook for Perla Villaları website leads',
    'description': """
Isolated Perla Villaları website → TCRM CRM lead integration.

- POST /webhook/tcrm/lead (HMAC-SHA256 v1, tenant UUID, durable idempotency)
- Disabled by default via tcrm.public_lead.enabled
- Tenant-local secret and CRM assignment configuration
- Does not modify AKOD, Meta, Twilio, or other tenant integrations
    """,
    'author': 'TCRM',
    'license': 'LGPL-3',
    'depends': ['crm', 'utm', 'sales_team'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/lead_source.xml',
        'data/ir_config_parameter.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
