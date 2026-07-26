# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    lunch_minimum_threshold = fields.Float()
    lunch_notify_message = fields.Html(
        default="""Your lunch has been delivered.
Enjoy your meal!""", translate=True)
