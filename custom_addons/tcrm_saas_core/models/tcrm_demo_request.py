# -*- coding: utf-8 -*-
from tcrm import models, fields, api

class DemoRequest(models.Model):
    _name = 'tcrm.demo.request'
    _description = 'TCRM Demo Request'
    _order = 'create_date desc'

    name = fields.Char(string='Applier Name', required=True)
    company_name = fields.Char(string='Company Name', required=True)
    email = fields.Char(string='Email', required=True)
    phone = fields.Char(string='Phone')
    notes = fields.Text(string='Notes')
    status = fields.Selection([
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ], string='Status', default='new', required=True, tracking=True)

    def action_mark_contacted(self):
        for rec in self:
            rec.status = 'contacted'

    def action_mark_accepted(self):
        for rec in self:
            rec.status = 'accepted'

    def action_mark_rejected(self):
        for rec in self:
            rec.status = 'rejected'
