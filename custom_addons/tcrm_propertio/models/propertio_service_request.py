# -*- coding: utf-8 -*-
from tcrm import models, fields, api
from datetime import date


class PropertioServiceRequest(models.Model):
    _name = 'propertio.service.request'
    _description = 'After-Sales Service Request'
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    unit_id = fields.Many2one('propertio.unit', string='Unit')
    sale_id = fields.Many2one('propertio.sale', string='Sale')
    company_id = fields.Many2one('res.company', string='Company', related='sale_id.company_id', store=True, readonly=True, index=True)
    request_type = fields.Selection([
        ('maintenance', 'Bakım'),
        ('defect', 'Eksiklik/Arıza'),
        ('document', 'Belge Talebi'),
        ('complaint', 'Şikayet'),
        ('info', 'Bilgi Talebi'),
        ('other', 'Diğer'),
    ], string='Type', required=True)
    priority = fields.Selection([
        ('low', 'Düşük'),
        ('normal', 'Normal'),
        ('high', 'Yüksek'),
        ('urgent', 'Acil'),
    ], default='normal')
    description = fields.Text(string='Description', required=True)
    assigned_to = fields.Many2one('res.users', string='Assigned To')
    deadline = fields.Date(string='Deadline')
    sla_status = fields.Selection([
        ('ok', 'On Time'),
        ('warning', 'Approaching'),
        ('breach', 'Overdue'),
    ], compute='_compute_sla_status', store=True)
    resolution = fields.Text(string='Resolution')
    resolved_date = fields.Date(string='Resolved Date')
    customer_rating = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
    ], string='Customer Rating')
    state = fields.Selection([
        ('new', 'Yeni'),
        ('in_progress', 'İşlemde'),
        ('resolved', 'Çözüldü'),
        ('closed', 'Kapatıldı'),
    ], default='new', required=True)
    photo_ids = fields.Many2many('ir.attachment', string='Photos')

    @api.depends('deadline', 'state')
    def _compute_sla_status(self):
        today = date.today()
        for r in self:
            if r.state in ('resolved', 'closed') or not r.deadline:
                r.sla_status = 'ok'
                continue
            if r.deadline < today:
                r.sla_status = 'breach'
            elif (r.deadline - today).days <= 2:
                r.sla_status = 'warning'
            else:
                r.sla_status = 'ok'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('propertio.service.request') or 'New'
        return super(PropertioServiceRequest, self).create(vals_list)
