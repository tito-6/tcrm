# -*- coding: utf-8 -*-
{
    'name': 'TCRM Web Enhance',
    'version': '1.1',
    'category': 'Hidden',
    'summary': 'TCRM UI/UX: branding, docs, spacing, toasts, dark mode, responsive polish',
    'depends': [
        'web',
        'website',
        'website_hr_recruitment',
        'crm',
        'tcrm_propertio',
    ],
    'data': [
        'views/website_branding.xml',
        'views/website_pages.xml',
        'views/docs_templates.xml',
        'views/demo_templates.xml',
        'views/help_links_views.xml',
        'data/fix_menu_icons.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tcrm_web_enhance/static/src/scss/tcrm_enhance.scss',
            'tcrm_web_enhance/static/src/js/toast_service.js',
            'tcrm_web_enhance/static/src/js/navbar_active.js',
            'tcrm_web_enhance/static/src/js/list_column_drag.js',
        ],
        'web.assets_frontend': [
            'tcrm_web_enhance/static/src/js/dropdown_fix.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
