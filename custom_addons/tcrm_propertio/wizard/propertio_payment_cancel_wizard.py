# -*- coding: utf-8 -*-
from tcrm import fields, models, _
from tcrm.exceptions import UserError


class PropertioPaymentCancelWizard(models.TransientModel):
    _name = 'propertio.payment.cancel.wizard'
    _description = 'Request cancellation of a posted payment'

    payment_id = fields.Many2one('propertio.payment', required=True, readonly=True)
    reason_code = fields.Selection([
        ('wrong_amount', 'Wrong Amount'),
        ('wrong_contract', 'Wrong Contract'),
        ('duplicate', 'Duplicate Entry'),
        ('customer_refund', 'Customer Refund / Para İade'),
        ('bank_error', 'Bank or POS Error'),
        ('other', 'Other'),
    ], string='Reason Code', required=True)
    explanation = fields.Text(string='Explanation', required=True)

    def action_submit(self, context=None):
        self.ensure_one()
        pay = self.payment_id
        if pay.state != 'posted':
            raise UserError(_('Only posted payments can be submitted for cancellation.'))
        Request = self.env['propertio.payment.cancel.request']
        if Request.search_count([('payment_id', '=', pay.id), ('state', '=', 'pending')]):
            raise UserError(_('A pending cancellation request already exists for this payment.'))
        Request.create({
            'payment_id': pay.id,
            'reason_code': self.reason_code,
            'reason': self.explanation,
        })
        pay.message_post(
            body=_('Cancellation requested. A sales manager must approve before the payment is reversed.'),
        )
        return {'type': 'ir.actions.act_window_close'}
