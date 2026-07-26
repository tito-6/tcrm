# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import models


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    _mailing_enabled = True
