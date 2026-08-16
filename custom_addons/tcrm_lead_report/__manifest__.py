# -*- coding: utf-8 -*-
{
    'name': 'Lead Raporu',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Executive Lead Havuzu analytics dashboard with marketing CPL',
    'description': """
Lead Raporu
===========
Production-grade CRM / Santral / Marketing Hub reporting dashboard:
KPI cards, charts, drill-down to Lead Havuzu, local marketing spend/CPL.
    """,
    'author': 'Tcrm S.A.',
    'license': 'LGPL-3',
    'depends': [
        'crm',
        'web',
        'tcrm_propertio',
        'tcrm_call_center',
        'tcrm_marketing_hub',
    ],
    'data': [
        'security/lead_report_groups.xml',
        'security/ir.model.access.csv',
        'security/lead_report_rules.xml',
        'data/status_map_data.xml',
        'views/status_map_views.xml',
        'views/lead_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tcrm_lead_report/static/src/lead_report/lead_report.scss',
            'tcrm_lead_report/static/src/lead_report/lead_report.xml',
            'tcrm_lead_report/static/src/lead_report/lead_report.js',
        ],
    },
    'installable': True,
    'application': False,
    'post_init_hook': 'post_init_hook',
}
