# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
{
    'name': 'Teklif Paneli',
    'version': '19.0.1.1.3',
    'category': 'Sales/CRM',
    'summary': 'Profesyonel teklif oluşturma, public passcode paylaşımı ve müşteri onayı',
    'description': (
        'AKOD CRM profesyonel teklif modülü: admin editör, güvenli public link + passcode, '
        'sunucu tarafı fiyatlandırma ve değiştirilemez onay snapshot.'
    ),
    'author': 'Tcrm S.A.',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'base_setup',
        'mail',
        'crm',
        'website',
    ],
    'data': [
        'security/offer_security.xml',
        'security/ir.model.access.csv',
        'security/offer_rules.xml',
        'data/ir_sequence.xml',
        'data/ir_cron.xml',
        'data/ir_config_parameter.xml',
        'data/catalogue_data.xml',
        'data/ahsen_template_data.xml',
        'data/akod_dijital_template_data.xml',
        'views/offer_views.xml',
        'views/offer_template_views.xml',
        'views/offer_catalogue_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/offer_from_template_views.xml',
        'views/menus.xml',
        'templates/public_teklif_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'tcrm_offer/static/src/scss/public_teklif.scss',
            'tcrm_offer/static/src/js/public_teklif.js',
        ],
        'web.assets_backend': [
            'tcrm_offer/static/src/scss/offer_backend.scss',
        ],
    },
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
}
