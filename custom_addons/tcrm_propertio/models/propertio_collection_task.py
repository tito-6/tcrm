# -*- coding: utf-8 -*-
from tcrm import models, fields, api, _


class PropertioCollectionTask(models.Model):
    _name = 'propertio.collection.task'
    _description = 'Collection Task (Overdue Follow-up)'
    _order = 'overdue_days desc, amount_due desc'

    installment_id = fields.Many2one(
        'propertio.installment', string='Installment', required=True, ondelete='cascade')
    company_id = fields.Many2one(
        'res.company', string='Company', related='installment_id.company_id', store=True, readonly=True, index=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', related='installment_id.partner_id', store=True, readonly=True)
    sale_id = fields.Many2one(
        'propertio.sale', string='Sale', related='installment_id.sale_id', store=True, readonly=True)
    overdue_days = fields.Integer(
        string='Overdue Days', related='installment_id.overdue_days', store=True, readonly=True)
    amount_due = fields.Monetary(
        string='Amount Due', related='installment_id.residual', store=True, readonly=True,
        currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='installment_id.currency_id', readonly=True)

    contact_attempts = fields.Integer(string='İletişim Denemesi', default=0)
    last_contact_date = fields.Date(string='Son İletişim')
    last_contact_result = fields.Selection([
        ('no_answer', 'Cevap Yok'),
        ('promise', 'Ödeme Sözü'),
        ('dispute', 'İtiraz'),
        ('partial', 'Kısmi Ödeme'),
        ('paid', 'Ödendi'),
    ], string='Son Sonuç')
    promise_date = fields.Date(string='Söz Tarihi')
    notes = fields.Text(string='Notlar')
    next_action_date = fields.Date(string='Sonraki Aksiyon')
    assigned_to = fields.Many2one('res.users', string='Atanan', default=lambda self: self.env.user)

    def action_log_call(self, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Log Call'),
            'res_model': 'propertio.log.call.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.id},
        }

    def action_mark_paid(self, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ödeme Gir'),
            'res_model': 'propertio.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_sale_id': self.sale_id.id,
                'default_payment_date': fields.Date.context_today(self),
                'default_exchange_rate': 1.0,
            },
        }

    def action_send_reminder(self, context=None):
        self.ensure_one()
        partner = self.partner_id
        raw_phone = partner._propertio_whatsapp_phone_raw()
        if raw_phone:
            import urllib.parse
            msg = _("Reminder: Your installment of %s is overdue. Please contact us.") % self.amount_due
            phone = raw_phone.replace(' ', '').replace('-', '').lstrip('+0')
            if not phone.startswith('90') and len(phone) == 10:
                phone = '90' + phone
            url = 'https://wa.me/' + phone + '?text=' + urllib.parse.quote(msg)
            return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new'}
        return {'type': 'ir.actions.act_window_close'}

    def action_generate_tasks(self, context=None):
        """Create or update collection tasks from overdue installments.

        Accepts optional ``context`` because list header buttons (display="always")
        may pass an extra positional argument via call_kw.
        """
        Installment = self.env['propertio.installment']
        Task = self.env['propertio.collection.task']
        overdue = Installment.search([
            ('is_paid', '=', False),
            ('overdue_days', '>', 0),
        ])
        for inst in overdue:
            task = Task.search([('installment_id', '=', inst.id)], limit=1)
            if not task:
                Task.create({'installment_id': inst.id})
        return True
