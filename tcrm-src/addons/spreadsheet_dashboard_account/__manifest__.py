# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for accounting",
    'version': '1.0',
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'account'],
    'data': [
        "data/dashboards.xml",
    ],
    'installable': True,
    'auto_install': ['account'],
    'author': 'Tcrm S.A.',
    'license': 'LGPL-3',
}
