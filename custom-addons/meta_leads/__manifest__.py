{
    'name': 'Meta Leads with Real-time Creative Integration',
    'version': '19.0.1.0.2',
    'summary': 'Complete Meta (Facebook/Instagram) leads integration with real-time ad creative fetching',
    'description': '''
    Enhanced Meta Lead Ads integration with:
    - Real-time webhook processing
    - Automatic ad creative fetching (images/videos)
    - Platform detection (Instagram vs Facebook)
    - Campaign tracking and UTM integration
    - Form response formatting
    - Visual creative previews in native Odoo UI
    ''',
    'category': 'Sales/CRM',
    'author': 'Your Company',
    'depends': ['crm', 'utm'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'views/mapping_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
