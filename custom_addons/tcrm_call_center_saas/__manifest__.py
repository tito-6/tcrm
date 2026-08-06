# -*- coding: utf-8 -*-
{
    'name': 'Santral ↔ TCRM Master',
    'version': '19.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Master-only Santral management on tcrm.tenant / Command Center',
    'description': 'Bridge: Santral control-plane UI for TCRM Master.',
    'author': 'Tcrm S.A.',
    'license': 'LGPL-3',
    'depends': [
        'tcrm_call_center',
        'tcrm_saas_core',
    ],
    'data': [
        'views/santral_master_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
