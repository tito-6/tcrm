# -*- coding: utf-8 -*-
from tcrm import models, fields, api


class PropertioCashRegister(models.Model):
    _name = 'propertio.cash.register'
    _description = 'Cash Register'

    name = fields.Char(string='Kasa Adı', required=True)
    company_id = fields.Many2one('res.company', string='Şirket', required=True, default=lambda self: self.env.company, index=True)
    currency_id = fields.Many2one('res.currency', string='Para Birimi', required=True, default=lambda self: self.env.company.currency_id)
    responsible_id = fields.Many2one('res.users', string='Sorumlu', default=lambda self: self.env.user)
    opening_balance = fields.Monetary(string='Açılış Bakiyesi', default=0, currency_field='currency_id')
    current_balance = fields.Monetary(string='Güncel Bakiye', compute='_compute_current_balance', store=True, currency_field='currency_id')
    transaction_ids = fields.One2many('propertio.cash.transaction', 'register_id', string='Hareketler')

    @api.depends('opening_balance', 'transaction_ids.amount', 'transaction_ids.type')
    def _compute_current_balance(self):
        for r in self:
            total = r.opening_balance
            for t in r.transaction_ids:
                total += t.amount if t.type == 'in' else -t.amount
            r.current_balance = total


class PropertioCashTransaction(models.Model):
    _name = 'propertio.cash.transaction'
    _description = 'Cash Transaction'

    register_id = fields.Many2one('propertio.cash.register', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='register_id.company_id', store=True, readonly=True, index=True)
    date = fields.Date(string='Tarih', default=fields.Date.context_today, required=True)
    type = fields.Selection([('in', 'Giriş'), ('out', 'Çıkış')], string='Tip', required=True, default='in')
    amount = fields.Monetary(string='Tutar', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Para Birimi', related='register_id.currency_id', readonly=True)
    reference = fields.Char(string='Referans')
    payment_id = fields.Many2one('propertio.payment', string='Ödeme')
    description = fields.Char(string='Açıklama')
