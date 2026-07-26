# -*- coding: utf-8 -*-
from tcrm import models, fields


class PropertioHolidayTr(models.Model):
    _name = 'propertio.holiday.tr'
    _description = 'Turkish Holiday'

    date = fields.Date(required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, index=True)
    name = fields.Char(required=True)
    type = fields.Selection([
        ('national', 'National'),
        ('religious', 'Religious'),
        ('regional', 'Regional'),
    ], string='Type', default='national')
