from tcrm import models, fields, api, _, SUPERUSER_ID
from tcrm.exceptions import UserError
from tcrm.tools.float_utils import float_compare, float_is_zero

class PropertioPayment(models.Model):
    _name = 'propertio.payment'
    _description = 'Property Collection/Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'propertio.audit.mixin']
    _order = 'payment_date desc'

    name = fields.Char(string='Ödeme Ref', required=True, copy=False, readonly=True, default='Yeni')
    
    partner_id = fields.Many2one('res.partner', string='Müşteri', required=True)
    sale_id = fields.Many2one('propertio.sale', string='Satış Sözleşmesi', required=True, domain="[('partner_id', '=', partner_id)]")
    company_id = fields.Many2one('res.company', string='Şirket', related='sale_id.company_id', store=True, readonly=True, index=True)
    
    amount = fields.Monetary(string='Ödenen Tutar', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Ödeme Para Birimi', required=True, default=lambda self: self.env.company.currency_id)
    
    payment_method = fields.Selection([
        ('bank', 'Havale/EFT'),
        ('cash', 'Nakit'),
        ('check', 'Çek'),
        ('senet', 'Senet'),
        ('credit_card', 'Kredi Kartı'),
        ('foreign_cash', 'Döviz Nakit'),
        ('installment_bank', 'Banka Taksiti'),
    ], string='Yöntem', required=True, default='bank')
    receipt_no = fields.Char(string='Makbuz No')
    cheque_no = fields.Char(string='Çek No')
    cheque_date = fields.Date(string='Çek Tarihi')
    vat_rate = fields.Float(string='KDV %', default=20.0)
    
    payment_date = fields.Date(string='Ödeme Tarihi', required=True, default=fields.Date.context_today)
    
    # Exchange Rate Logic
    # We store the rate used: how many [Sale Currency] units does 1 [Payment Currency] unit buy?
    # Or typically: Sale Currency Amount = Payment Amount * Rate (if rate is defined as Pay -> Sale)
    # Let's use TCRM standard: Rate = 1 / rate in database usually.
    # Let's make it simple for the user: "Covered Amount in Sale Currency"
    
    exchange_rate = fields.Float(string='Döviz Kuru', digits=(12, 6), help="Ödeme para birimini satış para birimine çevirme kuru", default=1.0)
    covered_amount = fields.Monetary(string='Karşılanan Tutar (Satış PB)', currency_field='sale_currency_id', compute='_compute_covered_amount', store=True, readonly=False)
    sale_currency_id = fields.Many2one('res.currency', related='sale_id.currency_id', readonly=True)

    state = fields.Selection([
        ('draft', 'Taslak'),
        ('posted', 'Onaylandı'),
        ('cancel', 'İptal Edildi')
    ], string='Durum', default='draft', tracking=True)
    active = fields.Boolean(default=True)
    is_reversal = fields.Boolean(string='İade / Ters Kayıt', readonly=True, copy=False)
    reversed_payment_id = fields.Many2one('propertio.payment', string='Orijinal Ödeme', readonly=True, copy=False)
    reversal_payment_id = fields.Many2one('propertio.payment', string='İade Kaydı', readonly=True, copy=False)
    cancellation_reason_code = fields.Selection([
        ('wrong_amount', 'Yanlış Tutar'),
        ('wrong_contract', 'Yanlış Sözleşme'),
        ('duplicate', 'Mükerrer Kayıt'),
        ('customer_refund', 'Müşteri İadesi / Para İade'),
        ('bank_error', 'Banka veya POS Hatası'),
        ('other', 'Diğer'),
    ], string='İptal Nedeni', readonly=True, copy=False)
    cancellation_explanation = fields.Text(string='İptal Açıklaması', readonly=True, copy=False)
    cancelled_by_id = fields.Many2one('res.users', string='İptal Eden', readonly=True, copy=False)
    cancelled_date = fields.Datetime(string='İptal Tarihi', readonly=True, copy=False)

    @api.onchange('payment_date', 'currency_id', 'sale_id')
    def _onchange_rate(self):
        if self.currency_id and self.sale_id and self.payment_date:
            if self.currency_id == self.sale_id.currency_id:
                self.exchange_rate = 1.0
            else:
                # Fetch rate from database for payment_date
                # We need conversion: Payment -> Sale
                # TCRM conversion: amount_to_text = currency_id._convert(amount, sale_currency, company, date)
                # We want the rate factor.
                
                # Check if we have TCMB rate integration?
                # The prompt implies we should auto-fetch or match.
                # Assuming _convert handles it if rates are in system.
                
                # Let's derive rate from _convert of 1.0 unit
                rate = self.currency_id._convert(1.0, self.sale_id.currency_id, self.env.company, self.payment_date)
                self.exchange_rate = rate

    @api.depends('amount', 'exchange_rate')
    def _compute_covered_amount(self):
        for record in self:
            record.covered_amount = record.amount * record.exchange_rate

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('propertio.payment') or 'New'
        records = super(PropertioPayment, self).create(vals_list)
        for rec in records:
            rec._audit_log('write', {'created': True}, sale_id=rec.sale_id.id)
        return records

    def write(self, vals):
        protected = {
            'partner_id', 'sale_id', 'amount', 'currency_id', 'payment_method', 'receipt_no',
            'cheque_no', 'cheque_date', 'vat_rate', 'payment_date', 'exchange_rate',
            'covered_amount', 'state',
        }
        if (
            not self.env.context.get('propertio_financial_internal')
            and protected.intersection(vals)
            and self.filtered(lambda p: p.state in ('posted', 'cancel'))
            and self.env.uid != SUPERUSER_ID
        ):
            for rec in self:
                rec._audit_log(
                    'blocked',
                    {'blocked_values': vals, 'message': 'Payment mutation requires cancellation/refund workflow.'},
                    sale_id=rec.sale_id.id,
                    original_model=rec._name,
                    original_res_id=rec.id,
                )
                rec.message_post(body=_('Blocked financial mutation. Use the Cancellation/Refund workflow instead.'))
            raise UserError(_('Posted or cancelled payments are immutable. Use Cancellation/Refund (Para İade).'))
        return super().write(vals)

    def unlink(self):
        if self.env.uid == SUPERUSER_ID:
            return super().unlink()
        for rec in self:
            rec._audit_log(
                'blocked',
                {'message': 'Deletion blocked. Use cancellation/refund workflow.'},
                sale_id=rec.sale_id.id,
                original_model=rec._name,
                original_res_id=rec.id,
            )
            rec.message_post(body=_('Deletion blocked by financial anti-fraud protocol. Use Cancellation/Refund (Para İade).'))
        raise UserError(_('Payments cannot be deleted. Use Cancellation/Refund (Para İade); only the Software Owner can physically delete.'))

    def action_post(self, context=None):
        for record in self:
            if record.amount <= 0:
                raise UserError(_("Payment amount must be positive."))
            
            # Allocation Logic (FIFO)
            to_allocate = record.covered_amount
            
            # Find unpaid installments, sorted by date
            installments = self.env['propertio.installment'].search([
                ('sale_id', '=', record.sale_id.id),
                ('is_paid', '=', False)
            ], order='date_due asc')
            
            for inst in installments:
                if to_allocate <= 0:
                    break
                
                needed = inst.residual
                if to_allocate >= needed:
                    # Fully cover this installment
                    inst.with_context(propertio_financial_internal=True).write({
                        'amount_paid': inst.amount_paid + needed,
                        'date_paid': record.payment_date,
                    })
                    to_allocate -= needed
                else:
                    # Partial cover
                    inst.with_context(propertio_financial_internal=True).write({
                        'amount_paid': inst.amount_paid + to_allocate,
                    })
                    to_allocate = 0
            
            # If to_allocate > 0, it means overpayment? 
            # For now, we ignore or leave it as extra? 
            # Spec doesn't define overpayment. We just stop when installments are exhausted.
            # Real world: Create a "Credit Note" or "Advance". For MVP, we simply update state.
            
            record.with_context(propertio_financial_internal=True).write({'state': 'posted'})

    def _reverse_posted_allocation(self):
        """Undo FIFO allocation using LIFO on installments (best effort without payment–installment lines)."""
        self.ensure_one()
        if self.state != 'posted':
            return
        to_undo = self.covered_amount
        currency = self.sale_id.currency_id
        rounding = currency.rounding or 0.01
        installments = self.env['propertio.installment'].search(
            [('sale_id', '=', self.sale_id.id)],
            order='date_due desc, id desc',
        )
        for inst in installments:
            if float_is_zero(to_undo, precision_rounding=rounding):
                break
            if float_is_zero(inst.amount_paid, precision_rounding=rounding):
                continue
            take = min(inst.amount_paid, to_undo)
            new_paid = inst.amount_paid - take
            vals = {'amount_paid': new_paid}
            if float_is_zero(new_paid, precision_rounding=rounding):
                vals['amount_paid'] = 0.0
                vals['date_paid'] = False
            elif float_compare(new_paid, inst.amount, precision_rounding=rounding) < 0:
                vals['date_paid'] = False
            inst.with_context(propertio_audit_skip=True, propertio_financial_internal=True).write(vals)
            to_undo -= take
        if not float_is_zero(to_undo, precision_rounding=rounding):
            raise UserError(_("Could not reverse the full allocation. Contact support."))

    def _action_cancel_posted_approved(self, reason_code=False, explanation=False, request=False):
        """Called only after a sales manager approves a cancellation request."""
        for rec in self:
            if rec.state != 'posted':
                raise UserError(_("Only posted payments can be reversed."))
            rec._reverse_posted_allocation()
            reversal = rec.copy({
                'name': self.env['ir.sequence'].next_by_code('propertio.payment') or _('Refund'),
                'amount': -rec.amount,
                'covered_amount': -rec.covered_amount,
                'state': 'posted',
                'is_reversal': True,
                'reversed_payment_id': rec.id,
                'cancellation_reason_code': reason_code,
                'cancellation_explanation': explanation,
                'cancelled_by_id': request.requester_id.id if request else self.env.user.id,
                'cancelled_date': fields.Datetime.now(),
            })
            rec.with_context(propertio_financial_internal=True).write({
                'state': 'cancel',
                'reversal_payment_id': reversal.id,
                'cancellation_reason_code': reason_code,
                'cancellation_explanation': explanation,
                'cancelled_by_id': request.requester_id.id if request else self.env.user.id,
                'cancelled_date': fields.Datetime.now(),
            })
            rec._audit_log(
                'reverse',
                {'reason_code': reason_code, 'explanation': explanation},
                sale_id=rec.sale_id.id,
                original_model=rec._name,
                original_res_id=rec.id,
                reversal_model=reversal._name,
                reversal_res_id=reversal.id,
                reason_code=reason_code,
                explanation=explanation,
                approved_by_id=self.env.user.id,
                approved_date=fields.Datetime.now(),
            )
            rec.message_post(
                body=_('Posted payment cancelled and refund/reversal entry %s created. Reason: %s') % (reversal.display_name, explanation or reason_code or ''),
            )
            reversal.message_post(body=_('Refund / Para İade reversal for original payment %s.') % rec.display_name)

    def action_open_cancel_request_wizard(self, context=None):
        self.ensure_one()
        if self.state != 'posted':
            raise UserError(_("Only posted payments require a cancellation request."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request payment cancellation'),
            'res_model': 'propertio.payment.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_payment_id': self.id},
        }

    def action_cancel(self, context=None):
        for record in self:
            if record.state == 'draft':
                record.with_context(propertio_financial_internal=True).write({'state': 'cancel'})
            elif record.state == 'posted':
                raise UserError(
                    _(
                        'Posted payments cannot be cancelled directly. '
                        'Use "Request cancellation" so a sales manager can approve the reversal.'
                    )
                )
