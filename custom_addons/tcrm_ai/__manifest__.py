{
    'name': 'TCRM AI',
    'version': '19.0.1.1.9',
    'category': 'Productivity',
    'summary': 'Groq-powered TCRM AI assistant with tenant-local settings and secure ORM tools',
    'description': """
TCRM AI
=======
- Software Owner grants TCRM AI entitlement from tcrm_master / Command Center
- Each database (master or tenant) keeps its own Groq API key and settings
- Chat uses approved read-only ORM tools; no SQL or cross-tenant access
- Native Discuss (tcrmBot) and HTML editor generate_text use Groq
- Initial provider: Groq (openai/gpt-oss-20b)
    """,
    'author': 'TCRM',
    'depends': ['base', 'web', 'mail', 'mail_bot', 'base_setup', 'crm', 'html_editor'],
    'data': [
        'security/tcrm_ai_security.xml',
        'security/ir.model.access.csv',
        'security/tcrm_ai_rules.xml',
        'data/tcrm_ai_data.xml',
        'data/tcrm_ai_provider_data.xml',
        'data/tcrm_ai_cron.xml',
        'views/tcrm_ai_settings_views.xml',
        'views/tcrm_ai_provider_views.xml',
        'views/tcrm_ai_conversation_views.xml',
        'views/tcrm_ai_usage_views.xml',
        'views/res_config_settings_views.xml',
        'views/tcrm_ai_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tcrm_ai/static/src/services/tcrm_ai_service.js',
            'tcrm_ai/static/src/tcrm_ai_chat/tcrm_ai_chat.scss',
            'tcrm_ai/static/src/tcrm_ai_chat/tcrm_ai_chat.js',
            'tcrm_ai/static/src/tcrm_ai_chat/tcrm_ai_chat.xml',
            'tcrm_ai/static/src/tcrm_ai_settings/tcrm_ai_settings.js',
            'tcrm_ai/static/src/tcrm_ai_settings/tcrm_ai_settings.xml',
        ],
        'web.assets_tests': [
            'tcrm_ai/static/tests/tours/tcrm_ai_tour.js',
        ],
        'web.qunit_suite_tests': [
            'tcrm_ai/static/tests/tcrm_ai_frontend_tests.js',
        ],
    },
    'external_dependencies': {'python': ['requests', 'cryptography']},
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
