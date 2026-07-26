# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
{
    'name': 'TCRM Mock Data',
    'version': '1.0',
    'category': 'Hidden/Tools',
    'summary': 'Coherent, idempotent, cross-linked demo/mock data for all TCRM modules',
    'description': """
TCRM Mock Data
==============
Builds one coherent "Nova Estates" business scenario shared across CRM, Sales,
Properties (Propertio), Contacts, Brokers, Payments and Dashboards.

The data is created through an idempotent Python builder (``tcrm.mock.builder``)
keyed on deterministic ``ir.model.data`` external IDs, so running it more than
once never creates duplicate records. It is (re)executed on every install/upgrade
of this module and can also be invoked manually::

    env['tcrm.mock.builder'].build_all()
""",
    'author': 'TCRM',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'contacts',
        'crm',
        'sale_management',
        'sale_crm',
        'account',
        'tcrm_propertio',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/build_mock_data.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'tcrm_mock_data/static/tests/tours/tcrm_smoke_tours.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
