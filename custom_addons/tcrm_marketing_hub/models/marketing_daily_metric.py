# -*- coding: utf-8 -*-
"""Local daily marketing spend cache — never fetched at report-request time."""
from __future__ import annotations

import json
import logging
from datetime import timedelta

from tcrm import api, fields, models, _

from ..services.zernio_client import ZernioError

_logger = logging.getLogger(__name__)

LEVEL_SELECTION = [
    ('campaign', 'Kampanya'),
    ('adset', 'Reklam Seti'),
    ('ad', 'Reklam'),
]

PLATFORM_SELECTION = [
    ('meta', 'Meta'),
    ('google', 'Google Ads'),
    ('unknown', 'Diğer'),
]

SYNC_STATUS_SELECTION = [
    ('ok', 'OK'),
    ('aggregate', 'Aggregate'),
    ('error', 'Hata'),
]


class TcrmMarketingDailyMetric(models.Model):
    _name = 'tcrm.marketing.daily.metric'
    _description = 'Marketing Daily Metric'
    _order = 'metric_date desc, id desc'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    level = fields.Selection(LEVEL_SELECTION, required=True, index=True)
    platform = fields.Selection(PLATFORM_SELECTION, default='unknown', index=True)
    platform_campaign_id = fields.Char(string='Kampanya ID', index=True)
    platform_adset_id = fields.Char(string='Reklam Seti ID', index=True)
    platform_ad_id = fields.Char(string='Reklam ID', index=True)
    entity_name = fields.Char(string='Ad')
    ad_account_id = fields.Many2one('tcrm.marketing.ad.account', index=True)
    metric_date = fields.Date(required=True, index=True)
    spend = fields.Float(string='Harcama', default=0.0)
    currency = fields.Char(default='TRY')
    impressions = fields.Float(default=0.0)
    clicks = fields.Float(default=0.0)
    leads_platform = fields.Float(string='Platform Lead', default=0.0)
    external_updated_at = fields.Datetime(string='Harici Güncelleme')
    last_sync_at = fields.Datetime(string='Son Senkron', default=fields.Datetime.now)
    sync_status = fields.Selection(SYNC_STATUS_SELECTION, default='ok', index=True)
    last_error = fields.Text(string='Son Hata')
    raw_json = fields.Text(string='Ham JSON')

    _sql_constraints = [
        (
            'uniq_daily_metric',
            'unique(company_id, level, platform, platform_campaign_id, platform_adset_id, platform_ad_id, metric_date)',
            'Bu günlük metrik zaten mevcut.',
        ),
    ]

    @api.model
    def _upsert_metric(self, vals):
        domain = [
            ('company_id', '=', vals['company_id']),
            ('level', '=', vals['level']),
            ('platform', '=', vals.get('platform') or 'unknown'),
            ('platform_campaign_id', '=', vals.get('platform_campaign_id') or ''),
            ('platform_adset_id', '=', vals.get('platform_adset_id') or ''),
            ('platform_ad_id', '=', vals.get('platform_ad_id') or ''),
            ('metric_date', '=', vals['metric_date']),
        ]
        existing = self.search(domain, limit=1)
        vals['last_sync_at'] = fields.Datetime.now()
        if existing:
            existing.write(vals)
            return existing
        return self.create(vals)

    @api.model
    def _spend_domain(self, company_id, date_from, date_to):
        domain = [('company_id', '=', company_id), ('level', '=', 'campaign')]
        d0 = fields.Date.from_string(date_from[:10]) if date_from else False
        d1 = fields.Date.from_string(date_to[:10]) if date_to else False
        if d0:
            domain.append(('metric_date', '>=', d0))
        if d1:
            domain.append(('metric_date', '<=', d1))
        return domain

    @api.model
    def _spend_total(self, company_id, date_from, date_to):
        records = self.search(self._spend_domain(company_id, date_from, date_to))
        if not records:
            return 0.0, False
        currency = records[0].currency or self.env.company.currency_id.name
        return sum(records.mapped('spend')), currency

    @api.model
    def _spend_for_campaign(self, company_id, platform_campaign_id, date_from, date_to):
        domain = self._spend_domain(company_id, date_from, date_to)
        domain.append(('platform_campaign_id', '=', str(platform_campaign_id)))
        records = self.search(domain)
        if not records:
            return 0.0, False
        currency = records[0].currency or self.env.company.currency_id.name
        return sum(records.mapped('spend')), currency

    @api.model
    def _detect_platform(self, item):
        src = (item.get('platform') or item.get('channelType') or '').lower()
        if 'google' in src:
            return 'google'
        if src in ('facebook', 'instagram', 'meta', 'metaads'):
            return 'meta'
        return 'unknown'

    @api.model
    def _extract_tree_metrics(self, tree, metric_date, ad_account, company):
        """Parse get_ads_tree response for a single-day window into upsert vals."""
        count = 0
        campaigns = tree.get('campaigns') or []
        for item in campaigns:
            metrics = item.get('metrics') or {}
            camp_id = str(item.get('platformCampaignId') or item.get('id') or item.get('_id') or '')
            camp_name = item.get('campaignName') or item.get('name') or camp_id
            if camp_id:
                self._upsert_metric({
                    'company_id': company.id,
                    'level': 'campaign',
                    'platform': self._detect_platform(item),
                    'platform_campaign_id': camp_id,
                    'platform_adset_id': '',
                    'platform_ad_id': '',
                    'entity_name': camp_name,
                    'ad_account_id': ad_account.id if ad_account else False,
                    'metric_date': metric_date,
                    'spend': float(metrics.get('spend') or 0),
                    'currency': item.get('currency') or ad_account.currency or company.currency_id.name,
                    'impressions': float(metrics.get('impressions') or 0),
                    'clicks': float(metrics.get('clicks') or metrics.get('linkClicks') or 0),
                    'leads_platform': float(metrics.get('leads') or metrics.get('conversions') or 0),
                    'sync_status': 'ok',
                    'last_error': False,
                    'raw_json': json.dumps(item, ensure_ascii=False, default=str)[:8000],
                })
                count += 1
            for aset in item.get('adSets') or item.get('adsets') or []:
                aset_metrics = aset.get('metrics') or {}
                aset_id = str(aset.get('platformAdSetId') or aset.get('id') or aset.get('_id') or '')
                aset_name = aset.get('adSetName') or aset.get('name') or aset_id
                if aset_id:
                    self._upsert_metric({
                        'company_id': company.id,
                        'level': 'adset',
                        'platform': self._detect_platform(aset) if aset.get('platform') else self._detect_platform(item),
                        'platform_campaign_id': camp_id or False,
                        'platform_adset_id': aset_id,
                        'platform_ad_id': '',
                        'entity_name': aset_name,
                        'ad_account_id': ad_account.id if ad_account else False,
                        'metric_date': metric_date,
                        'spend': float(aset_metrics.get('spend') or 0),
                        'currency': item.get('currency') or ad_account.currency or company.currency_id.name,
                        'impressions': float(aset_metrics.get('impressions') or 0),
                        'clicks': float(aset_metrics.get('clicks') or aset_metrics.get('linkClicks') or 0),
                        'sync_status': 'ok',
                        'last_error': False,
                    })
                    count += 1
                for ad in aset.get('ads') or []:
                    ad_metrics = ad.get('metrics') or {}
                    ad_id = str(ad.get('platformAdId') or ad.get('id') or ad.get('_id') or '')
                    ad_name = ad.get('name') or ad.get('adName') or ad_id
                    if ad_id:
                        self._upsert_metric({
                            'company_id': company.id,
                            'level': 'ad',
                            'platform': self._detect_platform(ad) if ad.get('platform') else self._detect_platform(item),
                            'platform_campaign_id': camp_id or False,
                            'platform_adset_id': aset_id or False,
                            'platform_ad_id': ad_id,
                            'entity_name': ad_name,
                            'ad_account_id': ad_account.id if ad_account else False,
                            'metric_date': metric_date,
                            'spend': float(ad_metrics.get('spend') or 0),
                            'currency': item.get('currency') or ad_account.currency or company.currency_id.name,
                            'impressions': float(ad_metrics.get('impressions') or 0),
                            'clicks': float(ad_metrics.get('clicks') or ad_metrics.get('linkClicks') or 0),
                            'sync_status': 'ok',
                            'last_error': False,
                        })
                        count += 1
        return count

    @api.model
    def _sync_day_for_account(self, ad_account, metric_date, client):
        company = ad_account.company_id
        day_str = fields.Date.to_string(metric_date)
        try:
            tree = client.get_ads_tree(
                page=1,
                limit=50,
                source='all',
                ad_account_id=ad_account.meta_act_id,
                account_id=ad_account.account_id.zernio_id if ad_account.account_id else None,
                date_from=day_str,
                date_to=day_str,
            )
            page = 1
            total = 0
            while page <= 40:
                if page > 1:
                    tree = client.get_ads_tree(
                        page=page,
                        limit=50,
                        source='all',
                        ad_account_id=ad_account.meta_act_id,
                        account_id=ad_account.account_id.zernio_id if ad_account.account_id else None,
                        date_from=day_str,
                        date_to=day_str,
                    )
                total += self._extract_tree_metrics(tree, metric_date, ad_account, company)
                pagination = tree.get('pagination') or {}
                total_pages = int(pagination.get('pages') or 1)
                campaigns = tree.get('campaigns') or []
                if page >= total_pages or not campaigns:
                    break
                page += 1
            return total, None
        except ZernioError as exc:
            _logger.warning('Daily metric sync failed %s %s: %s', ad_account.name, day_str, exc)
            self._upsert_metric({
                'company_id': company.id,
                'level': 'campaign',
                'platform': 'unknown',
                'platform_campaign_id': f'__error__{ad_account.id}',
                'platform_adset_id': '',
                'platform_ad_id': '',
                'entity_name': ad_account.name,
                'ad_account_id': ad_account.id,
                'metric_date': metric_date,
                'spend': 0.0,
                'currency': ad_account.currency or company.currency_id.name,
                'sync_status': 'error',
                'last_error': str(exc)[:2000],
            })
            return 0, str(exc)

    @api.model
    def sync_recent_metrics(self, days_back=7, company_id=None):
        """Sync daily spend for recent days. Called by cron or admin button."""
        companies = self.env['res.company'].browse([company_id]) if company_id else self.env.companies
        Profile = self.env['tcrm.marketing.profile']
        AdAccount = self.env['tcrm.marketing.ad.account']
        total_rows = 0
        errors = []
        today = fields.Date.context_today(self)
        for company in companies:
            profile = Profile.search([('company_id', '=', company.id)], limit=1)
            if not profile:
                continue
            try:
                client = profile._get_zernio_client()
            except Exception as exc:
                errors.append(f'{company.name}: {exc}')
                continue
            ad_accounts = AdAccount.search([('company_id', '=', company.id)])
            for day_offset in range(days_back + 1):
                metric_date = today - timedelta(days=day_offset)
                for ad_acc in ad_accounts:
                    if not ad_acc.meta_act_id:
                        continue
                    count, err = self._sync_day_for_account(ad_acc, metric_date, client)
                    total_rows += count
                    if err:
                        errors.append(f'{ad_acc.name} {metric_date}: {err}')
        return {
            'synced_rows': total_rows,
            'errors': errors[:20],
            'last_sync_at': fields.Datetime.to_string(fields.Datetime.now()),
        }

    @api.model
    def _cron_sync_daily_metrics(self):
        ICP = self.env['ir.config_parameter'].sudo()
        backfill_key = 'tcrm_marketing_hub.daily_metrics_initial_backfill_done'
        days_back = 5 if ICP.get_param(backfill_key) else 30
        for company in self.env.companies:
            try:
                self.sync_recent_metrics(days_back=days_back, company_id=company.id)
            except Exception as exc:
                _logger.exception('Marketing daily metric cron failed for %s: %s', company.name, exc)
        if not ICP.get_param(backfill_key):
            ICP.set_param(backfill_key, '1')
