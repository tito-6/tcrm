# -*- coding: utf-8 -*-
{
    'name': 'TCRM Web Enhance Sale',
    'version': '1.0.0',
    'category': 'Hidden',
    'summary': 'Remove Sales empty-state YouTube promo videos',
    'depends': ['sale', 'tcrm_web_enhance'],
    'assets': {
        'web.assets_backend': [
            'tcrm_web_enhance_sale/static/src/js/hide_sale_promo_video.js',
            'tcrm_web_enhance_sale/static/src/xml/hide_sale_promo_video.xml',
        ],
    },
    'installable': True,
    'auto_install': True,
    'application': False,
    'license': 'LGPL-3',
}
