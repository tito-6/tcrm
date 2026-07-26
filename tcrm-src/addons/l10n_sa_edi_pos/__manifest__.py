# Part of Tcrm. See LICENSE file for full copyright and licensing details.

{
    'name': 'Saudi Arabia - E-invoicing (Simplified)',
    'author': 'Tcrm S.A.',
    'countries': ['sa'],
    'version': '0.2',
    'depends': [
        'l10n_sa_pos',
        'l10n_sa_edi',
    ],
    'summary': """
        ZATCA E-Invoicing, support for PoS
    """,
    'description': """
E-invoice implementation for Saudi Arabia; Integration with ZATCA (POS)
    """,
    'category': 'Accounting/Localizations/EDI',
    'license': 'LGPL-3',
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_sa_edi_pos/static/src/**/*',
        ],
    }
}
