# Part of Tcrm. See LICENSE file for full copyright and licensing details.
from tcrm import models, fields


class L10n_LatamIdentificationType(models.Model):
    _inherit = "l10n_latam.identification.type"

    l10n_uy_dgi_code = fields.Char('DGI Code')
