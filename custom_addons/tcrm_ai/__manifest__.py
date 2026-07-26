{
    'name': 'TCRM AI',
    'version': '1.0',
    'category': 'Productivity',
    'summary': 'Gemini-powered AI: database, reports, real-time web, any question',
    'description': """
TCRM AI Engine
==============
- Settings: Gemini API key and model selection (all Gemini models).
- Reads current database (master or tenant) for the logged-in user.
- Generates reports, runs queries, answers natural language questions.
- Real-time internet data when needed.
- Renders tables and links to TCRM web views (e.g. payment plan → link to sale form).
    """,
    'author': 'TCRM',
    'depends': ['base', 'web', 'mail_bot', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'data/tcrm_ai_data.xml',
        'data/tcrm_ai_provider_data.xml',
        'views/tcrm_ai_settings_views.xml',
        'views/tcrm_ai_provider_views.xml',
        'views/res_config_settings_views.xml',
        'views/tcrm_ai_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tcrm_ai/static/src/tcrm_ai_chat/tcrm_ai_chat.js',
            'tcrm_ai/static/src/tcrm_ai_chat/tcrm_ai_chat.xml',
        ],
    },
    'external_dependencies': {'python': ['requests']},
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
