# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_rs_turnover_date = fields.Date(string='Turnover Date')
