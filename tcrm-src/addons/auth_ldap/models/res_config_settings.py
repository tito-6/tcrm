# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ldaps = fields.One2many(related='company_id.ldaps', string="LDAP Parameters", readonly=False)
