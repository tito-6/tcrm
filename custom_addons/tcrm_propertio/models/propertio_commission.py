# -*- coding: utf-8 -*-
from tcrm import models, fields, api


class PropertioCommissionRule(models.Model):
    _name = 'propertio.commission.rule'
    _description = 'Komisyon Kuralı'

    name = fields.Char(string='Ad', required=True)
    company_id = fields.Many2one('res.company', string='Şirket', required=True, default=lambda self: self.env.company, index=True)
    rule_type = fields.Selection([
        ('flat', 'Sabit Oran'),
        ('tiered', 'Kademeli'),
        ('target_bonus', 'Hedef Primi'),
        ('collection_bonus', 'Tahsilat Primi'),
    ], string='Tip', required=True)
    rate_pct = fields.Float(string='Oran %', default=1.0)
    active = fields.Boolean(string='Aktif', default=True)


class PropertioCommission(models.Model):
    _name = 'propertio.commission'
    _description = 'Komisyon Beyanı'
    _rec_name = 'display_name'

    display_name = fields.Char(string='Ad', compute='_compute_display_name', store=True)
    company_id = fields.Many2one('res.company', string='Şirket', required=True, default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one('res.users', string='Danışman', required=True)
    period_from = fields.Date(string='Dönem Başlangıç', required=True)
    period_to = fields.Date(string='Dönem Bitiş', required=True)
    gross_commission = fields.Monetary(string='Brüt Komisyon', compute='_compute_commission', store=True, currency_field='currency_id')
    deductions = fields.Monetary(string='Kesintiler', default=0, currency_field='currency_id')
    net_commission = fields.Monetary(string='Net Komisyon', compute='_compute_commission', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Para Birimi', default=lambda self: self.env.company.currency_id)
    state = fields.Selection([
        ('draft', 'Taslak'),
        ('approved', 'Onaylandı'),
        ('paid', 'Ödendi'),
    ], string='Durum', default='draft')

    @api.depends('user_id', 'period_from', 'period_to')
    def _compute_display_name(self):
        for r in self:
            if r.user_id and r.period_from and r.period_to:
                r.display_name = '%s (%s → %s)' % (r.user_id.name, r.period_from, r.period_to)
            elif r.user_id:
                r.display_name = r.user_id.name
            else:
                r.display_name = 'Komisyon'

    @api.depends('user_id', 'period_from', 'period_to', 'deductions')
    def _compute_commission(self):
        rule = self.env['propertio.commission.rule'].search([('rule_type', '=', 'flat'), ('active', '=', True)], limit=1)
        rate = (rule.rate_pct / 100.0) if rule else 0.01
        for r in self:
            sales = self.env['propertio.sale'].search([
                ('sales_person_id', '=', r.user_id.id),
                ('state', '=', 'confirmed'),
                ('date_sale', '>=', r.period_from),
                ('date_sale', '<=', r.period_to),
            ])
            r.gross_commission = sum(sales.mapped('sale_price')) * rate
            r.net_commission = r.gross_commission - r.deductions
