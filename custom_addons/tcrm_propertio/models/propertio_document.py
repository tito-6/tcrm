# -*- coding: utf-8 -*-
from tcrm import models, fields, api


class PropertioDocument(models.Model):
    _name = 'propertio.document'
    _description = 'Sale Document / Checklist'

    sale_id = fields.Many2one('propertio.sale', string='Satış', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Şirket', related='sale_id.company_id', store=True, readonly=True, index=True)
    partner_id = fields.Many2one('res.partner', related='sale_id.partner_id', store=True, readonly=True)
    doc_type = fields.Selection([
        ('id_copy', 'Kimlik Fotokopisi'),
        ('income_proof', 'Gelir Belgesi'),
        ('contract', 'Satış Sözleşmesi'),
        ('payment_plan', 'Ödeme Planı'),
        ('receipt', 'Makbuz'),
        ('tapu', 'Tapu Belgesi'),
        ('mortgage', 'İpotek Belgesi'),
        ('power_of_attorney', 'Vekaletname'),
        ('other', 'Diğer'),
    ], string='Belge Tipi', required=True)
    file = fields.Binary(string='Dosya', attachment=True)
    filename = fields.Char(string='Dosya Adı')
    uploaded_by = fields.Many2one('res.users', string='Yükleyen', default=lambda self: self.env.user)
    upload_date = fields.Datetime(string='Yükleme Tarihi', default=fields.Datetime.now)
    expiry_date = fields.Date(string='Son Geçerlilik')
    is_required = fields.Boolean(string='Satış İçin Zorunlu', default=False)
    verified = fields.Boolean(string='Doğrulandı')
    verified_by = fields.Many2one('res.users', string='Doğrulayan')
    notes = fields.Text(string='Notlar')
