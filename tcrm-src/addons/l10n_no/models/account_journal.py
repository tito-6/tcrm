# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    invoice_reference_model = fields.Selection(selection_add=[
        ('no', 'Norway (000001024000083)')
    ], ondelete={'no': lambda recs: recs.write({'invoice_reference_model': 'tcrm'})})
