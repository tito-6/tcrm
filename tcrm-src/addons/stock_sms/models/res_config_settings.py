# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    stock_sms_confirmation_template_id = fields.Many2one(
        related='company_id.stock_sms_confirmation_template_id', readonly=False)
