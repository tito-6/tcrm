# -*- coding: utf-8 -*-
from tcrm import models, fields, api


class PropertioLogCallWizard(models.TransientModel):
    _name = 'propertio.log.call.wizard'
    _description = 'Log Collection Call'

    task_id = fields.Many2one('propertio.collection.task', string='Task', required=True, ondelete='cascade')
    last_contact_result = fields.Selection([
        ('no_answer', 'No Answer'),
        ('promise', 'Payment Promised'),
        ('dispute', 'Payment Dispute'),
        ('partial', 'Partial Payment'),
        ('paid', 'Paid'),
    ], string='Result', required=True)
    promise_date = fields.Date(string='Promise Date')
    notes = fields.Text(string='Notes')
    next_action_date = fields.Date(string='Next Action Date')

    def action_confirm(self, context=None):
        self.ensure_one()
        self.task_id.write({
            'contact_attempts': self.task_id.contact_attempts + 1,
            'last_contact_date': fields.Date.context_today(self),
            'last_contact_result': self.last_contact_result,
            'promise_date': self.promise_date,
            'notes': (self.task_id.notes or '') + '\n' + (self.notes or '') if self.notes else self.task_id.notes,
            'next_action_date': self.next_action_date,
        })
        return {'type': 'ir.actions.act_window_close'}
