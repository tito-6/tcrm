# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    events_app_name = fields.Char('Events App Name', related='website_id.events_app_name', readonly=False)
