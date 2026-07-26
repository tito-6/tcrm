# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.


{
    'name': 'Mrp Repairs',
    'version': '1.0',
    'category': 'Supply Chain/Inventory',
    'depends': ['repair', 'mrp'],
    'data': [
        'views/production_views.xml',
        'views/repair_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Tcrm S.A.',
    'license': 'LGPL-3',
}
