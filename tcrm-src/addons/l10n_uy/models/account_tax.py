# Part of Tcrm. See LICENSE file for full copyright and licensing details.
from tcrm import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_uy_tax_category = fields.Selection([
        ('vat', 'VAT'),
    ], string="Tax Category", help="UY: Use to group the transactions in the Financial Reports required by DGI")
