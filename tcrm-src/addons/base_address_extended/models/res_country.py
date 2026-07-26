# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import fields, models


class ResCountry(models.Model):
    _inherit = 'res.country'

    enforce_cities = fields.Boolean(
        string='Enforce Cities',
        help="Check this box to ensure every address created in that country has a 'City' chosen "
             "in the list of the country's cities.")
