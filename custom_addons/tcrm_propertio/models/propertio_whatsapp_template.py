# -*- coding: utf-8 -*-
from tcrm import models, fields, api
import urllib.parse


class PropertioWhatsappTemplate(models.Model):
    _name = 'propertio.whatsapp.template'
    _description = 'WhatsApp Message Template'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, index=True)
    body = fields.Text(string='Message Body', required=True,
                      help='Use placeholders: {customer_name}, {amount}, {due_date}, {contract_ref}, {unit_name}, {sale_price}')
    model = fields.Selection([
        ('res.partner', 'Contact'),
        ('propertio.sale', 'Sale Contract'),
        ('propertio.installment', 'Installment'),
        ('propertio.offer', 'Offer'),
    ], string='Model', required=True)
    active = fields.Boolean(default=True)

    def _replace_placeholders(self, body, record):
        """Replace placeholders in body with record values."""
        if not record:
            return body
        repl = {}
        if hasattr(record, 'name'):
            repl['customer_name'] = record.name if record._name == 'res.partner' else getattr(record.partner_id, 'name', '') or record.name
        else:
            repl['customer_name'] = ''
        repl['contract_ref'] = getattr(record, 'name', '') if record._name == 'propertio.sale' else getattr(getattr(record, 'sale_id', None), 'name', '')
        repl['unit_name'] = ''
        if hasattr(record, 'unit_id') and record.unit_id:
            repl['unit_name'] = record.unit_id.name
        elif hasattr(record, 'sale_id') and record.sale_id and record.sale_id.unit_id:
            repl['unit_name'] = record.sale_id.unit_id.name
        repl['amount'] = ''
        repl['due_date'] = ''
        repl['sale_price'] = ''
        if hasattr(record, 'residual'):
            repl['amount'] = '%.2f' % (record.residual or 0)
        if hasattr(record, 'amount'):
            repl['amount'] = '%.2f' % (record.amount or 0)
        if hasattr(record, 'sale_price'):
            repl['sale_price'] = '%.2f' % (record.sale_price or 0)
        if hasattr(record, 'date_due') and record.date_due:
            repl['due_date'] = str(record.date_due)
        out = body
        for k, v in repl.items():
            out = out.replace('{' + k + '}', str(v))
        return out

    def get_whatsapp_url(self, record):
        """Return wa.me URL for record using this template."""
        self.ensure_one()
        partner = None
        if record._name == 'res.partner':
            partner = record
        elif hasattr(record, 'partner_id'):
            partner = record.partner_id
        if not partner:
            return None
        raw = partner._propertio_whatsapp_phone_raw()
        phone = str(raw).replace(' ', '').replace('-', '').lstrip('+0')
        if len(phone) == 10 and not phone.startswith('90'):
            phone = '90' + phone
        if not phone:
            return None
        msg = self._replace_placeholders(self.body, record)
        return 'https://wa.me/' + phone + '?text=' + urllib.parse.quote(msg)
