# -*- coding: utf-8 -*-
from tcrm import models, fields, api
from datetime import date


class PropertioTarget(models.Model):
    _name = 'propertio.target'
    _description = 'Sales / Collection Target'

    company_id = fields.Many2one('res.company', string='Şirket', required=True, default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one('res.users', string='Danışman', required=True)
    period_type = fields.Selection([
        ('monthly', 'Aylık'),
        ('quarterly', 'Çeyreklik'),
        ('yearly', 'Yıllık'),
    ], string='Dönem Tipi', default='monthly', required=True)
    date_from = fields.Date(string='Başlangıç', required=True)
    date_to = fields.Date(string='Bitiş', required=True)
    project_id = fields.Many2one('propertio.project', string='Proje')
    target_units = fields.Integer(string='Hedef Birim', default=0)
    target_amount = fields.Monetary(string='Hedef Tutar', currency_field='currency_id', default=0)
    target_collection = fields.Monetary(string='Hedef Tahsilat', currency_field='currency_id', default=0)
    currency_id = fields.Many2one('res.currency', string='Para Birimi', default=lambda self: self.env.company.currency_id)
    actual_units = fields.Integer(string='Gerçekleşen Birim', compute='_compute_actuals', store=True)
    actual_amount = fields.Monetary(string='Gerçekleşen Tutar', compute='_compute_actuals', store=True, currency_field='currency_id')
    actual_collection = fields.Monetary(string='Gerçekleşen Tahsilat', compute='_compute_actuals', store=True, currency_field='currency_id')
    achievement_pct = fields.Float(compute='_compute_actuals', store=True, string='Başarı %')
    state = fields.Selection([
        ('draft', 'Taslak'),
        ('active', 'Aktif'),
        ('done', 'Tamamlandı'),
    ], string='Durum', default='draft')

    @api.depends('date_from', 'date_to', 'user_id', 'project_id')
    def _compute_actuals(self):
        Sale = self.env['propertio.sale']
        Payment = self.env['propertio.payment']
        for r in self:
            domain = [
                ('sales_person_id', '=', r.user_id.id),
                ('state', '=', 'confirmed'),
                ('date_sale', '>=', r.date_from),
                ('date_sale', '<=', r.date_to),
            ]
            if r.project_id:
                domain.append(('project_id', '=', r.project_id.id))
            sales = Sale.search(domain)
            r.actual_units = len(sales)
            r.actual_amount = sum(sales.mapped('sale_price'))
            payments = Payment.search([
                ('state', '=', 'posted'),
                ('payment_date', '>=', r.date_from),
                ('payment_date', '<=', r.date_to),
                ('sale_id', 'in', sales.ids),
            ])
            r.actual_collection = sum(payments.mapped('amount'))
            r.achievement_pct = (r.actual_amount / r.target_amount * 100) if r.target_amount else 0
