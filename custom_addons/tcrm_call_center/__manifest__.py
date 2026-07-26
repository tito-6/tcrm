# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
{
    'name': 'Santral',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Tenant-isolated browser calling (Twilio) for TCRM CRM',
    'description': """
Santral (tcrm_call_center)
==========================
Outbound browser calling from CRM with verified caller ID, recording,
call history and protected playback. Configuration is always tenant-local;
there is no global Twilio fallback across tenants.
    """,
    'author': 'Tcrm S.A.',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'base_setup',
        'web',
        'mail',
        'crm',
        'calendar',
        'project_todo',
        'tcrm_propertio',
        'tcrm_saas_core',
    ],
    'data': [
        'security/call_security.xml',
        'security/ir.model.access.csv',
        'security/call_rules.xml',
        'data/ir_sequence.xml',
        'data/call_cron.xml',
        'views/call_provider_config_views.xml',
        'views/call_record_views.xml',
        'views/res_config_settings_views.xml',
        'views/crm_lead_views.xml',
        'views/res_partner_views.xml',
        'views/santral_master_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tcrm_call_center/static/src/scss/active_menu.scss',
            'tcrm_call_center/static/src/services/call_center_service.js',
            'tcrm_call_center/static/src/dialer/dialer.scss',
            'tcrm_call_center/static/src/dialer/dialer.xml',
            'tcrm_call_center/static/src/dialer/dialer.js',
            'tcrm_call_center/static/src/patches/kanban_call_button.js',
            'tcrm_call_center/static/src/patches/phone_field_patch.js',
            'tcrm_call_center/static/src/patches/phone_field_patch.xml',
        ],
        'web.assets_tests': [
            'tcrm_call_center/static/tests/tours/santral_dialer_tour.js',
        ],
        'web.qunit_suite_tests': [
            'tcrm_call_center/static/tests/santral_frontend_tests.js',
        ],
    },
    'external_dependencies': {
        'python': ['twilio', 'cryptography', 'requests'],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
}
