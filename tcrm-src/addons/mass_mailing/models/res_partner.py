# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import models


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _mailing_enabled = True
