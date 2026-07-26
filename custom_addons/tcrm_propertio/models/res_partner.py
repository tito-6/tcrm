# -*- coding: utf-8 -*-
from tcrm import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    nationality = fields.Many2one('res.country', string='Nationality')
    id_type = fields.Selection([
        ('tc', 'TC Kimlik'),
        ('passport', 'Pasaport'),
        ('foreign', 'Yabancı Kimlik'),
    ], string='ID Type')
    id_number = fields.Char(string='ID Number')
    birth_date = fields.Date(string='Birth Date')
    marital_status = fields.Selection([
        ('single', 'Bekar'),
        ('married', 'Evli'),
    ], string='Marital Status')
    spouse_name = fields.Char(string='Spouse Name')
    occupation = fields.Char(string='Occupation')
    monthly_income = fields.Monetary(string='Monthly Income', currency_field='currency_id')
    budget_min = fields.Monetary(string='Budget Min', currency_field='currency_id')
    budget_max = fields.Monetary(string='Budget Max', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    preferred_project_ids = fields.Many2many(
        'propertio.project', 'res_partner_propertio_project_rel',
        'partner_id', 'project_id', string='Preferred Projects')
    preferred_unit_type = fields.Many2many(
        'propertio.unit.category', 'res_partner_propertio_unit_category_rel',
        'partner_id', 'category_id', string='Preferred Unit Type')
    lead_source = fields.Selection([
        ('website', 'Web Sitesi'),
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('sahibinden', 'Sahibinden'),
        ('whatsapp', 'WhatsApp'),
        ('landline', 'Sabit Hat'),
        ('indoor', 'Ofis / Showroom'),
        ('referral', 'Referans'),
        ('google_ads', 'Google Ads'),
        ('walk_in', 'Ofis Ziyareti'),
        ('exhibition', 'Fuar'),
        ('other', 'Diğer'),
    ], string='Müşteri Kaynağı')
    how_did_you_hear = fields.Char(string='Bizi nereden duydunuz?')
    whatsapp_number = fields.Char(string='WhatsApp Numarası')
    tc_kimlik_no = fields.Char(string='TC Kimlik No', size=11)
    vergi_no = fields.Char(string='Vergi No')
    vergi_dairesi = fields.Char(string='Vergi Dairesi')
    mahalle = fields.Char(string='Mahalle')

    total_purchased_value = fields.Monetary(
        string='Total Purchased', compute='_compute_real_estate_totals', currency_field='currency_id')
    total_paid = fields.Monetary(
        string='Total Paid', compute='_compute_real_estate_totals', currency_field='currency_id')
    outstanding_balance = fields.Monetary(
        string='Outstanding', compute='_compute_real_estate_totals', currency_field='currency_id')
    risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Risk Level', compute='_compute_risk_level')

    @api.depends()
    def _compute_real_estate_totals(self):
        Sale = self.env['propertio.sale']
        for p in self:
            sales = Sale.search([('partner_id', '=', p.id), ('state', '=', 'confirmed')])
            p.total_purchased_value = sum(s.sale_price for s in sales)
            p.total_paid = sum(s.total_paid for s in sales)
            p.outstanding_balance = sum(s.balance for s in sales)

    @api.depends()
    def _compute_risk_level(self):
        for p in self:
            overdue = self.env['propertio.installment'].search_count([
                ('partner_id', '=', p.id),
                ('is_paid', '=', False),
                ('overdue_days', '>=', 15),
            ])
            p.risk_level = 'high' if overdue > 2 else ('medium' if overdue > 0 else 'low')

    def _propertio_whatsapp_phone_raw(self):
        """Best phone string for wa.me (TCRM base partner has no ``mobile`` field)."""
        self.ensure_one()
        wa = (self.whatsapp_number or '').strip()
        if wa:
            return wa
        if 'mobile' in self._fields:
            m = (self.mobile or '').strip()
            if m:
                return m
        return (self.phone or '').strip()

    def action_send_whatsapp(self, context=None):
        self.ensure_one()
        template = self.env['propertio.whatsapp.template'].search([
            ('model', '=', 'res.partner'),
            ('active', '=', True),
        ], limit=1)
        url = template.get_whatsapp_url(self) if template else None
        if not url:
            phone = self._propertio_whatsapp_phone_raw()
            if phone:
                import urllib.parse
                digits = phone.replace(' ', '').replace('-', '').lstrip('+0')
                if len(digits) == 10 and not digits.startswith('90'):
                    digits = '90' + digits
                url = 'https://wa.me/' + digits + '?text=' + urllib.parse.quote('Hello')
        return {
            'type': 'ir.actions.act_url',
            'url': url or '#',
            'target': 'new',
        }

    def action_real_estate_history(self, context=None):
        self.ensure_one()
        return {
            'name': 'Real Estate History',
            'type': 'ir.actions.act_window',
            'res_model': 'propertio.sale',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
