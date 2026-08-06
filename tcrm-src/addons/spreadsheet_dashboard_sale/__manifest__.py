# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.
{
    'name': "Spreadsheet dashboard for sales",
    'version': '1.0',
    'category': 'Productivity/Dashboard',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': ['spreadsheet_dashboard', 'sale'],
    'data': [
        "data/dashboards.xml",
    ],
    'auto_install': ['sale'],
    'author': 'Tcrm S.A.',
    'license': 'LGPL-3',
}
