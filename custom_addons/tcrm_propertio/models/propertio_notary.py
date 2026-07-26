# -*- coding: utf-8 -*-
from tcrm import models, fields


class PropertioNotary(models.Model):
    _name = 'propertio.notary'
    _description = 'Notary Appointment'

    sale_id = fields.Many2one('propertio.sale', string='Satış', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Şirket', related='sale_id.company_id', store=True, readonly=True, index=True)
    partner_id = fields.Many2one('res.partner', related='sale_id.partner_id', store=True, readonly=True)
    notary_office = fields.Char(string='Noterlik')
    appointment_datetime = fields.Datetime(string='Randevu')
    appointment_type = fields.Selection([
        ('promise_sale', 'Ön Protokol/Vaat'),
        ('sale', 'Satış'),
        ('power_of_attorney', 'Vekaletname'),
        ('cancellation', 'İptal'),
    ], string='Tip')
    documents_ready = fields.Boolean(string='Belgeler Alındı')
    completed = fields.Boolean(string='Tamamlandı')
    notes = fields.Text(string='Notlar')
