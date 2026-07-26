# -*- coding: utf-8 -*-
# Part of tcrm. See LICENSE file for full copyright and licensing details.

{
    'name': 'tcrmBot',
    'version': '1.2',
    'category': 'Productivity/Discuss',
    'summary': 'Add tcrmBot in discussions',
    'website': 'https://www.tcrm.com/app/discuss',
    'depends': ['mail'],
    'auto_install': True,
    'installable': True,
    'data': [
        'views/res_users_views.xml',
        'data/mailbot_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mail_bot/static/src/scss/tcrmbot_style.scss',
        ],
    },
    'author': 'tcrm S.A.',
    'license': 'LGPL-3',
}
