{
    'name': 'TCRM Theme',
    'version': '18.0.1.0.0',
    'summary': 'TCRM White-Labeling & Branding',
    'description': """
        Comprehensive white-labeling for Odoo 18.
        - Replaces Odoo branding with TCRM.
        - Updates system logos and icons.
        - Overrides colors and fonts.
    """,
    'author': 'Antigravity',
    'category': 'Theme/Backend',
    'depends': ['base', 'web', 'mail'],
    'data': [
        # 'views/web_client_templates.xml',
        # 'views/user_menu_templates.xml',
        # 'views/login_templates.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'theme_tcrm/static/src/scss/primary_variables.scss',
        ],
        'web.assets_backend': [
            'theme_tcrm/static/src/scss/overrides.scss',
            'theme_tcrm/static/src/xml/about_dialog.xml',
            'theme_tcrm/static/src/js/user_menu.js',
        ],
        'web.assets_frontend': [
            'theme_tcrm/static/src/scss/primary_variables.scss',
            'theme_tcrm/static/src/scss/overrides.scss',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'auto_install': True,
    'license': 'LGPL-3',
}
