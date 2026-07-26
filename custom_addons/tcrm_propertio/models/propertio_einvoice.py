# -*- coding: utf-8 -*-
from tcrm import models, fields


class PropertioEinvoice(models.Model):
    _name = 'propertio.einvoice'
    _description = 'E-Invoice / E-Arşiv (Turkey)'

    sale_id = fields.Many2one('propertio.sale', string='Sale')
    payment_id = fields.Many2one('propertio.payment', string='Payment')
    company_id = fields.Many2one('res.company', string='Company', related='sale_id.company_id', store=True, readonly=True, index=True)
    invoice_type = fields.Selection([
        ('e_fatura', 'E-Fatura'),
        ('e_arsiv', 'E-Arşiv'),
    ], string='Type', required=True)
    invoice_date = fields.Date(default=fields.Date.context_today)
    due_date = fields.Date()
    invoice_no = fields.Char(string='GIB Invoice No')
    uuid = fields.Char(string='GIB UUID')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='draft')
    xml_content = fields.Text()
    pdf_content = fields.Binary()
    gib_response = fields.Text()
    error_message = fields.Text()
