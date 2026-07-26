# -*- coding: utf-8 -*-
from tcrm import models, fields


class PropertioTitleDeed(models.Model):
    _name = 'propertio.title.deed'
    _description = 'Title Deed / Tapu Tracking'

    sale_id = fields.Many2one('propertio.sale', string='Satış', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Şirket', related='sale_id.company_id', store=True, readonly=True, index=True)
    unit_id = fields.Many2one('propertio.unit', related='sale_id.unit_id', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', related='sale_id.partner_id', store=True, readonly=True)

    tapu_no = fields.Char(string='Tapu No')
    tapu_date = fields.Date(string='Tapu Tarihi')
    tapu_type = fields.Selection([
        ('kat_irtifak', 'Kat İrtifakı'),
        ('kat_mulkiyet', 'Kat Mülkiyeti'),
    ], string='Tapu Tipi')
    tapu_office = fields.Char(string='Tapu Müdürlüğü')
    tapu_cost = fields.Monetary(string='Tapu Masrafı', currency_field='currency_id')
    tapu_cost_paid = fields.Boolean(string='Tapu Masrafı Ödendi')
    currency_id = fields.Many2one('res.currency', related='sale_id.currency_id', readonly=True)
    tapu_appointment = fields.Datetime(string='Randevu')
    mortgage_exists = fields.Boolean(string='İpotek Var')
    mortgage_bank = fields.Many2one('res.partner', string='İpotek Bankası')
    mortgage_released = fields.Boolean(string='İpotek Kaldırıldı')
    state = fields.Selection([
        ('pending', 'Bekliyor'),
        ('appointment', 'Randevu Var'),
        ('transferred', 'Tapu Devredildi'),
    ], string='Durum', default='pending')
    document_ids = fields.Many2many('ir.attachment', string='Belgeler')
