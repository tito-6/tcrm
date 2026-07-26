# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
{
    'name': 'Marketing Hub',
    'version': '1.5.3',
    'category': 'Marketing',
    'summary': 'Meta Business hub: reklamlar, lead formları, CRM entegrasyonu (Zernio)',
    'description': """
Marketing Hub
=============
Full-page Meta Business workspace powered by Zernio API:

* Hub app (OWL) — assets, ads monitor, Meta leads, inbox, posts
* Lead Gen forms + leads → crm.lead
* Ad account selector and campaign monitoring
* Instagram / Facebook publish, inbox, comments
    """,
    'author': 'Tcrm S.A.',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'base_setup',
        'web',
        'mail',
        'crm',
        'utm',
    ],
    'data': [
        'security/marketing_security.xml',
        'security/ir.model.access.csv',
        'views/marketing_profile_views.xml',
        'views/marketing_account_views.xml',
        'views/marketing_post_views.xml',
        'views/marketing_inbox_views.xml',
        'views/marketing_ads_views.xml',
        'views/marketing_analytics_views.xml',
        'views/marketing_lead_views.xml',
        'views/crm_lead_views.xml',
        'wizard/compose_post_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/marketing_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tcrm_marketing_hub/static/src/marketing_hub/marketing_hub.scss',
            'tcrm_marketing_hub/static/src/marketing_hub/marketing_hub.xml',
            'tcrm_marketing_hub/static/src/marketing_hub/marketing_hub.js',
        ],
    },
    'external_dependencies': {
        'python': ['requests'],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
}
