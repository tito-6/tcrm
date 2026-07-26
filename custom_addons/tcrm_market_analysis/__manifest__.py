# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
{
    'name': 'Piyasa Analizi',
    'version': '1.1.1',
    'category': 'Real Estate',
    'summary': 'Tenant-isolated real-estate market intelligence for TCRM',
    'description': """
Piyasa Analizi (tcrm_market_analysis)
=====================================
Market-listing intelligence with cascading TR location filters and optional
public Sahibinden collection (no login). CAPTCHA/auth/anti-bot bypass is
refused — blocked responses stop the job with the exact error.
    """,
    'author': 'Tcrm S.A.',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'crm',
        'tcrm_propertio',
    ],
    'data': [
        'security/market_security.xml',
        'security/ir.model.access.csv',
        'security/market_rules.xml',
        'data/market_sequence.xml',
        'data/market_cron.xml',
        'views/market_source_views.xml',
        'views/market_listing_views.xml',
        'views/market_import_views.xml',
        'views/market_analysis_views.xml',
        'views/market_comparable_views.xml',
        'wizard/market_import_wizard_views.xml',
        'views/market_menus.xml',
        'views/crm_lead_views.xml',
        'views/propertio_unit_views.xml',
    ],
    'demo': [
        'demo/market_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tcrm_market_analysis/static/src/market_analysis/market_analysis.scss',
            'tcrm_market_analysis/static/src/market_analysis/market_analysis.xml',
            'tcrm_market_analysis/static/src/market_analysis/market_analysis.js',
        ],
    },
    'external_dependencies': {
        'python': ['openpyxl', 'requests', 'bs4'],
    },
    # Temporarily disabled in the UI; keep code for a later re-enable.
    'installable': True,
    'application': False,
    'post_init_hook': 'post_init_hook',
}
