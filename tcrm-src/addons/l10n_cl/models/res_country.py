# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.
from tcrm import fields, models


class ResCountry(models.Model):
    _inherit = 'res.country'

    l10n_cl_customs_code = fields.Char('Customs Code')
    l10n_cl_customs_name = fields.Char('Customs Name')
    l10n_cl_customs_abbreviation = fields.Char('Customs Abbreviation')
