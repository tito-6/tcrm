# -*- coding: utf-8 -*-
import json

from tcrm import fields, models


class TcrmOfferApproval(models.Model):
    _name = 'tcrm.offer.approval'
    _description = 'Teklif Onayı'
    _order = 'approved_at desc'

    offer_id = fields.Many2one(
        'tcrm.offer', string='Teklif', required=True, ondelete='restrict', index=True,
    )
    company_id = fields.Many2one(
        related='offer_id.company_id', store=True, readonly=True,
    )
    approver_name = fields.Char(string='Yetkili Ad Soyad', required=True)
    approver_company = fields.Char(string='Firma / Unvan')
    approver_email = fields.Char(string='E-posta', required=True)
    approver_phone = fields.Char(string='Telefon')
    selected_item_ids_json = fields.Text(string='Seçilen Kalem ID JSON', required=True)
    ad_budget = fields.Float(string='Seçilen Reklam Bütçesi', digits=(16, 2))
    net_total = fields.Monetary(string='Net Toplam', currency_field='currency_id')
    tax_total = fields.Monetary(string='KDV', currency_field='currency_id')
    gross_total = fields.Monetary(string='Genel Toplam', currency_field='currency_id')
    monthly_net = fields.Monetary(string='Aylık Net', currency_field='currency_id')
    one_time_net = fields.Monetary(string='Tek Seferlik Net', currency_field='currency_id')
    per_session_net = fields.Monetary(string='Seans Net', currency_field='currency_id')
    currency_id = fields.Many2one(related='offer_id.currency_id', store=True, readonly=True)
    snapshot_json = fields.Text(string='Snapshot JSON', required=True)
    snapshot_checksum = fields.Char(string='Snapshot Checksum', required=True)
    terms_version = fields.Char(string='Şartlar Versiyonu')
    kvkk_version = fields.Char(string='KVKK Versiyonu')
    accepted_services = fields.Boolean(string='Hizmet Onayı', default=True)
    accepted_terms = fields.Boolean(string='Şart Onayı', default=True)
    accepted_kvkk = fields.Boolean(string='KVKK Onayı', default=True)
    approved_at = fields.Datetime(string='Onay Zamanı', required=True)
    ip_masked = fields.Char(string='IP (maskeli)')
    user_agent = fields.Char(string='User-Agent')
    idempotency_key = fields.Char(string='Idempotency Key', index=True)

    _offer_approval_unique = models.Constraint(
        'unique(offer_id)',
        'Bir teklif için yalnızca bir onay kaydı olabilir.',
    )
    _offer_approval_idempotency_unique = models.Constraint(
        'unique(idempotency_key)',
        'Idempotency key benzersiz olmalıdır.',
    )

    def get_selected_item_ids(self):
        self.ensure_one()
        try:
            return json.loads(self.selected_item_ids_json or '[]')
        except json.JSONDecodeError:
            return []

    def get_snapshot(self):
        self.ensure_one()
        try:
            return json.loads(self.snapshot_json or '{}')
        except json.JSONDecodeError:
            return {}
