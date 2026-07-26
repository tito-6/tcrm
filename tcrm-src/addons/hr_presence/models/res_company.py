# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    hr_presence_last_compute_date = fields.Datetime()
