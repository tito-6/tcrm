# -*- coding: utf-8 -*-
try:
    from tcrm import models, fields, api, _
    from tcrm.exceptions import ValidationError
except ImportError:
    from odoo import models, fields, api, _
    from odoo.exceptions import ValidationError

from datetime import datetime, timedelta

class RealEstateProject(models.Model):
    _name = 'tcrm.real.estate.project'
    _description = 'Gayrimenkul Projesi'
    _order = 'name'

    name = fields.Char(string='Proje Adı', required=True)
    code = fields.Char(string='Proje Kodu')
    city = fields.Char(string='Şehir / İl')
    district = fields.Char(string='İlçe / Bölge')
    address = fields.Text(string='Proje Adresi')
    developer_company = fields.Char(string='Geliştirici / İnşaat Firması')
    delivery_date = fields.Date(string='Teslim Tarihi')
    
    total_blocks = fields.Integer(string='Blok Sayısı', default=1)
    total_units = fields.Integer(string='Toplam Bağımsız Bölüm', compute='_compute_unit_counts', store=True)
    available_units = fields.Integer(string='Satılık (Mevcut)', compute='_compute_unit_counts', store=True)
    reserved_units = fields.Integer(string='Rezerve / Opsiyonlu', compute='_compute_unit_counts', store=True)
    sold_units = fields.Integer(string='Satılan', compute='_compute_unit_counts', store=True)

    project_image = fields.Binary(string='Proje Görseli')
    master_plan_file = fields.Binary(string='Vaziyet & Kat Planı Dokümanı')
    master_plan_filename = fields.Char(string='Kat Planı Dosya Adı')
    description = fields.Text(string='Proje Açıklaması ve Detayları')
    
    unit_ids = fields.One2many('tcrm.real.estate.unit', 'project_id', string='Bağımsız Bölümler')
    active = fields.Boolean(default=True)

    @api.depends('unit_ids', 'unit_ids.state')
    def _compute_unit_counts(self):
        for proj in self:
            units = proj.unit_ids
            proj.total_units = len(units)
            proj.available_units = len(units.filtered(lambda u: u.state == 'satilik'))
            proj.reserved_units = len(units.filtered(lambda u: u.state in ['rezerve', 'opsiyonlu']))
            proj.sold_units = len(units.filtered(lambda u: u.state == 'satildi'))


class RealEstateUnit(models.Model):
    _name = 'tcrm.real.estate.unit'
    _description = 'Bağımsız Bölüm / Daire Stok Kartı'
    _order = 'project_id, block_name, floor_number, unit_number'

    name = fields.Char(string='Daire Kodu / No', compute='_compute_name', store=True)
    project_id = fields.Many2one('tcrm.real.estate.project', string='Proje', required=True, ondelete='cascade')
    block_name = fields.Char(string='Blok Adı / Kodu', default='A Blok')
    floor_number = fields.Integer(string='Kat No', default=1)
    unit_number = fields.Char(string='Kapı / Daire No', required=True)
    
    unit_type = fields.Selection([
        ('1+0', '1+0 (Stüdyo)'),
        ('1+1', '1+1'),
        ('2+1', '2+1'),
        ('3+1', '3+1'),
        ('4+1', '4+1'),
        ('5+1', '5+1 ve Üzeri'),
        ('dublex', 'Dubleks'),
        ('villa', 'Villa / Müstakil'),
        ('ticari', 'Ticari / Dükkan / Ofis'),
    ], string='Daire Tipi', default='2+1', required=True)

    net_m2 = fields.Float(string='Net M²')
    gross_m2 = fields.Float(string='Brüt M²')
    facade = fields.Selection([
        ('kuzey', 'Kuzey'),
        ('guney', 'Güney'),
        ('dogu', 'Doğu'),
        ('bati', 'Batı'),
        ('kuzey_dogu', 'Kuzey-Doğu'),
        ('kuzey_bati', 'Kuzey-Batı'),
        ('guney_dogu', 'Güney-Doğu'),
        ('guney_bati', 'Güney-Batı'),
        ('panoramik', 'Panoramik / Deniz / Peyzaj'),
    ], string='Cephe')

    list_price = fields.Float(string='Liste Satış Fiyatı (TL)', required=True)
    currency_id = fields.Many2one('res.currency', string='Para Birimi', default=lambda self: self.env.company.currency_id)
    
    state = fields.Selection([
        ('satilik', 'Satılık (Mevcut)'),
        ('opsiyonlu', 'Opsiyonlu'),
        ('rezerve', 'Rezerve Edildi'),
        ('satildi', 'Satıldı'),
    ], string='Stok Durumu', default='satilik', required=True, tracking=True)

    reservation_partner_id = fields.Many2one('res.partner', string='Rezerve Eden Müşteri')
    reservation_date = fields.Datetime(string='Rezervasyon Tarihi')
    reservation_expiry_date = fields.Datetime(string='Rezervasyon Bitiş Tarihi')

    floor_plan_image = fields.Binary(string='Daire Kat Planı Görseli')
    notes = fields.Text(string='Özel Notlar')

    @api.depends('project_id.name', 'block_name', 'unit_number')
    def _compute_name(self):
        for unit in self:
            proj_name = unit.project_id.name if unit.project_id else ''
            unit.name = f"{proj_name} - {unit.block_name or ''} D:{unit.unit_number or ''}".strip()

    def action_set_reserved(self):
        for unit in self:
            unit.state = 'rezerve'
            unit.reservation_date = fields.Datetime.now()
            unit.reservation_expiry_date = fields.Datetime.now() + timedelta(days=3)

    def action_set_available(self):
        for unit in self:
            unit.state = 'satilik'
            unit.reservation_partner_id = False
            unit.reservation_date = False
            unit.reservation_expiry_date = False

    def action_set_sold(self):
        for unit in self:
            unit.state = 'satildi'


class RealEstatePaymentPlan(models.Model):
    _name = 'tcrm.real.estate.payment.plan'
    _description = 'Gayrimenkul Ödeme Planı Hesaplayıcı'

    name = fields.Char(string='Plan Adı', compute='_compute_name', store=True)
    lead_id = fields.Many2one('crm.lead', string='Müşteri Talebi (Lead)', ondelete='cascade')
    unit_id = fields.Many2one('tcrm.real.estate.unit', string='Seçilen Daire / Bağımsız Bölüm', required=True)
    
    total_price = fields.Float(string='Toplam Satış Fiyatı', related='unit_id.list_price', store=True, readonly=False)
    discount_rate = fields.Float(string='İndirim Oranı (%)', default=0.0)
    discounted_price = fields.Float(string='Net Anlaşma Fiyatı', compute='_compute_financials', store=True)

    payment_type = fields.Selection([
        ('pesin', 'Peşin Ödeme'),
        ('vadeli', 'Standart Vadeli Taksit'),
        ('ara_odeme', 'Peşinat + Taksit + Ara Ödeme'),
        ('ozel', 'Özel Kampanya'),
    ], string='Ödeme Tipi', default='vadeli', required=True)

    down_payment_rate = fields.Float(string='Peşinat Oranı (%)', default=20.0)
    down_payment_amount = fields.Float(string='Peşinat Tutarı', compute='_compute_financials', store=True)

    installment_count = fields.Integer(string='Taksit Sayısı (Ay)', default=24)
    monthly_installment_amount = fields.Float(string='Aylık Taksit Tutarı', compute='_compute_financials', store=True)

    interim_payment_count = fields.Integer(string='Ara Ödeme Sayısı', default=0)
    interim_payment_amount = fields.Float(string='Ara Ödeme Başına Tutar', default=0.0)
    
    delivery_payment_amount = fields.Float(string='Teslimat Günü Ödemesi', default=0.0)
    notes = fields.Text(string='Ödeme Planı Notları')

    @api.depends('unit_id.name', 'lead_id.name')
    def _compute_name(self):
        for plan in self:
            plan.name = f"Ödeme Planı - {plan.unit_id.name or ''}".strip()

    @api.depends('total_price', 'discount_rate', 'down_payment_rate', 'installment_count', 'interim_payment_count', 'interim_payment_amount', 'delivery_payment_amount')
    def _compute_financials(self):
        for plan in self:
            net_price = plan.total_price * (1.0 - (plan.discount_rate / 100.0))
            plan.discounted_price = net_price
            
            down = net_price * (plan.down_payment_rate / 100.0)
            plan.down_payment_amount = down

            total_interim = plan.interim_payment_count * plan.interim_payment_amount
            remaining_for_installments = net_price - down - total_interim - plan.delivery_payment_amount
            
            if plan.installment_count > 0:
                plan.monthly_installment_amount = max(0.0, remaining_for_installments / plan.installment_count)
            else:
                plan.monthly_installment_amount = 0.0


class CrmLeadRealEstate(models.Model):
    _inherit = 'crm.lead'

    interested_project_id = fields.Many2one('tcrm.real.estate.project', string='İlgilendiği Proje')
    interested_unit_type = fields.Selection([
        ('1+0', '1+0 (Stüdyo)'),
        ('1+1', '1+1'),
        ('2+1', '2+1'),
        ('3+1', '3+1'),
        ('4+1', '4+1'),
        ('5+1', '5+1 ve Üzeri'),
        ('dublex', 'Dubleks'),
        ('villa', 'Villa / Müstakil'),
        ('ticari', 'Ticari / Dükkan / Ofis'),
    ], string='Aranan Daire Tipi')

    budget_min = fields.Float(string='Minimum Bütçe (TL)')
    budget_max = fields.Float(string='Maksimum Bütçe (TL)')
    selected_unit_id = fields.Many2one('tcrm.real.estate.unit', string='Seçilen Daire / Bağımsız Bölüm')
    payment_plan_ids = fields.One2many('tcrm.real.estate.payment.plan', 'lead_id', string='Ödeme Planları')

    meeting_notes = fields.Text(string='Görüşme ve Sunum Notları')
    preferred_facade = fields.Char(string='Tercih Edilen Cephe / Manzara')
