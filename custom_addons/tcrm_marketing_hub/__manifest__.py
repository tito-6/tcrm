# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
{
    'name': 'Marketing Hub',
    'version': '1.6.13',
    'category': 'Marketing',
    'summary': 'Meta + Google Ads hub: kreatifler, reklamlar, lead formları (Zernio)',
    'description': """
Marketing Hub
=============
Full-page Meta + Google Ads workspace powered by Zernio API:

* Hub app (OWL) — assets, Meta/Google ads, creatives gallery, Meta leads, inbox
* Lead Gen forms + leads → crm.lead
* Google Ads: campaigns, keywords, GAQL insights, IMAGE/YOUTUBE assets
* Meta creatives library (images, videos, reels)
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
        'data/ir_cron.xml',
        'views/marketing_profile_views.xml',
        'views/marketing_account_views.xml',
        'views/marketing_post_views.xml',
        'views/marketing_inbox_views.xml',
        'views/marketing_ads_views.xml',
        'views/marketing_google_views.xml',
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
