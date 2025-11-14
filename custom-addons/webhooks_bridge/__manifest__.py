{
    'name': 'Webhooks Bridge',
    'version': '17.0.1.0.0',
    'summary': 'Expose webhook endpoints for Meta and Google',
    'description': 'Adds public endpoints /webhooks/meta and /webhooks/google for testing webhooks with ngrok.',
    'category': 'Tools',
    'author': 'Your Company',
    'depends': ['base', 'crm'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}