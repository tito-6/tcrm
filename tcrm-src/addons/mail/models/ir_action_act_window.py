# -*- coding: utf-8 -*-
from tcrm import fields, models


class IrActionsAct_WindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[
        ('activity', 'Activity')
    ], ondelete={'activity': 'cascade'})
