# -*- coding: utf-8 -*-
import json
import logging

from tcrm import _, api, fields, models

_logger = logging.getLogger(__name__)


class MarketingAdset(models.Model):
    """Meta Ad Set model (reklam seti) under Meta Campaigns."""

    _name = 'tcrm.marketing.adset'
    _description = 'Meta Reklam Seti'
    _order = 'write_date desc, id desc'

    name = fields.Char(string='Reklam Seti Adı', required=True)
    platform_adset_id = fields.Char(string='Meta AdSet ID', required=True, index=True)
    zernio_id = fields.Char(string='Zernio AdSet ID', index=True)
    status = fields.Char(string='Durum', default='ACTIVE')
    daily_budget = fields.Float(string='Günlük Bütçe')
    lifetime_budget = fields.Float(string='Toplam Bütçe')
    bid_amount = fields.Float(string='Teklif Miktarı')
    optimization_goal = fields.Char(string='Optimiyasyon Hedefi')
    billing_event = fields.Char(string='Faturalandırma Etkinliği')
    targeting_summary = fields.Char(string='Hedef Kitle Özeti')

    campaign_id = fields.Many2one(
        'tcrm.marketing.campaign',
        string='Kampanya',
        required=True,
        ondelete='cascade',
        index=True,
    )
    ad_account_id = fields.Many2one(
        'tcrm.marketing.ad.account',
        string='Reklam Hesabı',
        ondelete='set null',
        index=True,
    )
    account_id = fields.Many2one(
        'tcrm.marketing.account',
        string='Sosyal Hesap',
        ondelete='set null',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Şirket',
        required=True,
        default=lambda s: s.env.company,
    )

    ad_ids = fields.One2many('tcrm.marketing.meta.ad', 'adset_id', string='Reklamlar')
    ad_count = fields.Integer(string='Reklam Sayısı', compute='_compute_ad_count')

    spend = fields.Float(string='Harcama')
    impressions = fields.Float(string='Gösterim')
    clicks = fields.Float(string='Tıklama')
    last_sync_at = fields.Datetime(string='Son Senkron')
    raw_json = fields.Text(groups='tcrm_marketing_hub.group_marketing_admin')

    _sql_constraints = [
        ('platform_adset_uniq', 'unique(platform_adset_id)', 'Bu Meta reklam seti zaten kayıtlı.'),
    ]

    @api.depends('ad_ids')
    def _compute_ad_count(self):
        for rec in self:
            rec.ad_count = len(rec.ad_ids)
