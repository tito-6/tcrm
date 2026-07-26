# Part of Tcrm. See LICENSE file for full copyright and licensing details.

{
    "name": "Cloud Storage Azure",
    "summary": """Store chatter attachments in the Azure cloud""",
    "category": "Technical Settings",
    "version": "1.0",
    "depends": ["cloud_storage"],
    "data": [
        "views/settings.xml",
    ],
    "uninstall_hook": "uninstall_hook",
    'author': 'Tcrm S.A.',
    'license': 'LGPL-3',
}
