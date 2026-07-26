# -*- coding: utf-8 -*-
from tcrm import models, fields, api


class PropertioHandover(models.Model):
    _name = 'propertio.handover'
    _description = 'Unit Handover / Teslim'
    _order = 'handover_date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    sale_id = fields.Many2one('propertio.sale', string='Sale', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='sale_id.company_id', store=True, readonly=True, index=True)
    unit_id = fields.Many2one('propertio.unit', related='sale_id.unit_id', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', related='sale_id.partner_id', store=True, readonly=True)

    payment_complete = fields.Boolean(compute='_compute_payment_complete', store=True)
    title_deed_done = fields.Boolean(string='Title Deed Done')
    keys_handed = fields.Boolean(string='Keys Handed')
    handover_date = fields.Date(string='Handover Date')
    handover_protocol = fields.Binary(string='Handover Protocol')
    state = fields.Selection([
        ('pending', 'Bekliyor'),
        ('scheduled', 'Randevu Verildi'),
        ('done', 'Teslim Edildi'),
        ('issue', 'Sorun Var'),
    ], string='Status', default='pending', required=True)

    checklist_ids = fields.One2many('propertio.handover.checklist', 'handover_id', string='Checklist')
    issue_ids = fields.One2many('propertio.handover.issue', 'handover_id', string='Issues')

    @api.depends('sale_id.installment_ids', 'sale_id.installment_ids.is_paid')
    def _compute_payment_complete(self):
        for r in self:
            if not r.sale_id or not r.sale_id.installment_ids:
                r.payment_complete = False
                continue
            r.payment_complete = all(r.sale_id.installment_ids.mapped('is_paid'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('propertio.handover') or 'New'
        return super(PropertioHandover, self).create(vals_list)


class PropertioHandoverChecklist(models.Model):
    _name = 'propertio.handover.checklist'
    _description = 'Handover Checklist Item'

    handover_id = fields.Many2one('propertio.handover', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='handover_id.company_id', store=True, readonly=True, index=True)
    name = fields.Char(string='Item', required=True)
    done = fields.Boolean(string='Done', default=False)


class PropertioHandoverIssue(models.Model):
    _name = 'propertio.handover.issue'
    _description = 'Handover Issue / Defect'

    handover_id = fields.Many2one('propertio.handover', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='handover_id.company_id', store=True, readonly=True, index=True)
    description = fields.Text(string='Description', required=True)
    reported_date = fields.Date(default=fields.Date.context_today)
    resolved_date = fields.Date()
    assigned_to = fields.Many2one('res.users', string='Assigned To')
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], default='normal')
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ], default='open')
