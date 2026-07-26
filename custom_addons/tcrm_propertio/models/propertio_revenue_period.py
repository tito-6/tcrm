# -*- coding: utf-8 -*-
from tcrm import models, fields, api
from datetime import date


class PropertioRevenuePeriod(models.Model):
    _name = 'propertio.revenue.period'
    _description = 'Revenue Period Snapshot'

    period = fields.Char(string='Period', required=True)  # e.g. '2026-03'
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, index=True)
    project_id = fields.Many2one('propertio.project', string='Project')
    total_contracted = fields.Monetary(currency_field='currency_id', default=0)
    total_collected = fields.Monetary(currency_field='currency_id', default=0)
    total_outstanding = fields.Monetary(currency_field='currency_id', default=0)
    total_overdue = fields.Monetary(currency_field='currency_id', default=0)
    collection_rate = fields.Float(compute='_compute_collection_rate', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    new_sales_count = fields.Integer(default=0)
    new_sales_value = fields.Monetary(currency_field='currency_id', default=0)
    cancelled_sales_count = fields.Integer(default=0)
    cancelled_sales_value = fields.Monetary(currency_field='currency_id', default=0)

    @api.depends('total_contracted', 'total_collected')
    def _compute_collection_rate(self):
        for r in self:
            r.collection_rate = (r.total_collected / r.total_contracted * 100) if r.total_contracted else 0
