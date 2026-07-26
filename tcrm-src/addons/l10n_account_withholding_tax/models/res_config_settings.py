# Part of Tcrm. See LICENSE file for full copyright and licensing details.
from tcrm import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ------------------
    # Fields declaration
    # ------------------

    withholding_tax_base_account_id = fields.Many2one(
        related='company_id.withholding_tax_base_account_id',
        readonly=False,
    )
