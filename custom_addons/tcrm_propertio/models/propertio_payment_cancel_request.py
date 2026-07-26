# -*- coding: utf-8 -*-
from tcrm import api, fields, models, _
from tcrm.exceptions import UserError


class PropertioPaymentCancelRequest(models.Model):
    _name = 'propertio.payment.cancel.request'
    _description = 'Posted payment cancellation (sales manager approval)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    payment_id = fields.Many2one(
        'propertio.payment',
        string='Payment',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='payment_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )
    reason = fields.Text(string='Reason')
    reason_code = fields.Selection([
        ('wrong_amount', 'Wrong Amount'),
        ('wrong_contract', 'Wrong Contract'),
        ('duplicate', 'Duplicate Entry'),
        ('customer_refund', 'Customer Refund / Para İade'),
        ('bank_error', 'Bank or POS Error'),
        ('other', 'Other'),
    ], string='Reason Code', required=True, default='other', tracking=True)
    requester_id = fields.Many2one(
        'res.users',
        string='Requested by',
        default=lambda s: s.env.user.id,
        readonly=True,
    )
    state = fields.Selection(
        [
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='pending',
        tracking=True,
    )
    approver_id = fields.Many2one('res.users', string='Approved by', readonly=True)
    approval_date = fields.Datetime(string='Approval date', readonly=True)
    rejection_reason = fields.Text(string='Rejection reason')
    manager_notified = fields.Boolean(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('propertio.payment.cancel.request') or 'New'
        records = super().create(vals_list)
        for rec in records:
            rec.payment_id._audit_log(
                'approval',
                {'request': rec.name, 'reason_code': rec.reason_code, 'reason': rec.reason},
                sale_id=rec.payment_id.sale_id.id,
                original_model=rec.payment_id._name,
                original_res_id=rec.payment_id.id,
                reason_code=rec.reason_code,
                explanation=rec.reason,
                requires_manager_approval=True,
            )
            rec.payment_id.message_post(body=_('Cancellation/refund request %s created. Reason: %s') % (rec.name, rec.reason))
            rec._notify_manager_if_repeated()
        return records

    def _manager_users(self):
        domain = [
            ('active', '=', True),
            ('company_id', '=', self.company_id.id),
            ('propertio_role', 'in', ['manager', 'admin']),
        ]
        users = self.env['res.users'].sudo().search(domain)
        if users:
            return users
        return self.env['res.users'].sudo().search([('active', '=', True), ('groups_id', 'in', [self.env.ref('base.group_system').id])])

    def _notify_manager_if_repeated(self):
        self.ensure_one()
        sale = self.payment_id.sale_id
        count = self.env['propertio.payment.cancel.request'].sudo().search_count([
            ('payment_id.sale_id', '=', sale.id),
            ('id', '!=', self.id),
        ]) + 1
        if count <= 2:
            return
        managers = self._manager_users()
        body = _('%s has entered and requested deletion/correction %s times for payment records on contract %s. Please approve or reject request %s.') % (
            self.requester_id.display_name,
            count,
            sale.display_name,
            self.display_name,
        )
        self.message_post(body=body, partner_ids=managers.mapped('partner_id').ids)
        self.payment_id.message_post(body=body, partner_ids=managers.mapped('partner_id').ids)
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for manager in managers:
            self.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                user_id=manager.id,
                summary=_('Approve repeated payment correction'),
                note=body,
            )
        self.sudo().write({'manager_notified': True})

    def _user_can_approve(self):
        self.ensure_one()
        user = self.env.user
        role = getattr(user, 'propertio_role', None) or 'sales'
        return role in ('manager', 'admin') or user.has_group('base.group_system')

    def action_approve(self, context=None):
        for rec in self:
            if not rec._user_can_approve():
                raise UserError(_('Only Propertio Managers or Admins can approve payment cancellations.'))
            if rec.state != 'pending':
                raise UserError(_('This request is not pending.'))
            rec.payment_id._action_cancel_posted_approved(
                reason_code=rec.reason_code,
                explanation=rec.reason,
                request=rec,
            )
            rec.write({
                'state': 'approved',
                'approver_id': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })
            rec.message_post(body=_('Cancellation approved and payment reversed.'))
        return True

    def action_reject(self, context=None):
        for rec in self:
            if not rec._user_can_approve():
                raise UserError(_('Only Propertio Managers or Admins can reject cancellation requests.'))
            if rec.state != 'pending':
                raise UserError(_('This request is not pending.'))
            rec.write({
                'state': 'rejected',
                'approver_id': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })
            rec.message_post(body=rec.rejection_reason or _('Cancellation request rejected.'))
        return True
