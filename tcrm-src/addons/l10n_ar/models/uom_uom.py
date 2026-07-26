# Part of Tcrm. See LICENSE file for full copyright and licensing details.
from tcrm import fields, models


class UomUom(models.Model):
    _inherit = 'uom.uom'

    l10n_ar_afip_code = fields.Char('Code', help='Argentina: This code will be used on electronic invoice.')
