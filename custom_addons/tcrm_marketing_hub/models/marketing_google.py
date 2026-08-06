# -*- coding: utf-8 -*-
"""Google Ads models + sync (Zernio googleads platform)."""
import json
import logging

from tcrm import _, api, fields, models
from tcrm.exceptions import UserError

from ..services.zernio_client import ZernioError

_logger = logging.getLogger(__name__)

DEFAULT_GAQL_CAMPAIGNS = (
    "SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type, "
    "metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions, "
    "metrics.ctr, metrics.average_cpc "
    "FROM campaign WHERE segments.date DURING LAST_30_DAYS"
)


class MarketingGoogleKeyword(models.Model):
    _name = 'tcrm.marketing.google.keyword'
    _description = 'Google Ads Anahtar Kelime'
    _order = 'campaign_name, keyword'
    _rec_name = 'keyword'

    zernio_id = fields.Char(string='Zernio ID', index=True, copy=False)
    keyword = fields.Char(string='Anahtar Kelime', required=True, index=True)
    match_type = fields.Selection(
        [
            ('exact', 'Exact'),
            ('phrase', 'Phrase'),
            ('broad', 'Broad'),
            ('unknown', 'Bilinmiyor'),
        ],
        string='Eşleme',
        default='unknown',
        index=True,
    )
    status = fields.Selection(
        [
            ('active', 'Aktif'),
            ('paused', 'Duraklatıldı'),
            ('unknown', 'Bilinmiyor'),
        ],
        string='Durum',
        default='unknown',
        index=True,
    )
    negative = fields.Boolean(string='Negatif', default=False, index=True)
    campaign_id_remote = fields.Char(string='Kampanya ID', index=True)
    campaign_name = fields.Char(string='Kampanya')
    campaign_status = fields.Char(string='Kampanya Durumu')
    adset_id_remote = fields.Char(string='Reklam Grubu ID', index=True)
    adset_name = fields.Char(string='Reklam Grubu')
    adset_status = fields.Char(string='Reklam Grubu Durumu')
    account_id = fields.Many2one(
        'tcrm.marketing.account',
        string='Google Ads Hesabı',
        ondelete='cascade',
        index=True,
    )
    ad_account_id = fields.Many2one(
        'tcrm.marketing.ad.account',
        string='Müşteri Hesabı',
        ondelete='set null',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Şirket',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    synced_at = fields.Datetime(string='Senkron')
    raw_json = fields.Text(groups='tcrm_marketing_hub.group_marketing_admin')

    _sql_constraints = [
        (
            'zernio_keyword_uniq',
            'unique(zernio_id)',
            'Bu anahtar kelime zaten kayıtlı.',
        ),
    ]

    @api.model
    def _map_match(self, value):
        v = (value or '').lower().strip()
        if v in ('exact', 'phrase', 'broad'):
            return v
        return 'unknown'

    @api.model
    def _map_status(self, value):
        v = (value or '').lower().strip()
        if v in ('active', 'enabled'):
            return 'active'
        if v in ('paused', 'disabled'):
            return 'paused'
        return 'unknown'

    @api.model
    def _upsert_from_remote(self, item, *, social, ad_account):
        zid = str(item.get('id') or item.get('_id') or '')
        text = (item.get('keyword') or '').strip()
        if not text:
            return self.browse()
        vals = {
            'zernio_id': zid or False,
            'keyword': text,
            'match_type': self._map_match(item.get('matchType')),
            'status': self._map_status(item.get('status')),
            'negative': bool(item.get('negative')),
            'campaign_id_remote': str(item.get('campaignId') or '') or False,
            'campaign_name': item.get('campaignName') or False,
            'campaign_status': item.get('campaignStatus') or False,
            'adset_id_remote': str(item.get('adSetId') or '') or False,
            'adset_name': item.get('adSetName') or False,
            'adset_status': item.get('adSetStatus') or False,
            'account_id': social.id if social else False,
            'ad_account_id': ad_account.id if ad_account else False,
            'company_id': (
                ad_account.company_id.id if ad_account
                else (social.company_id.id if social else self.env.company.id)
            ),
            'synced_at': fields.Datetime.now(),
            'raw_json': json.dumps(item, ensure_ascii=False, default=str)[:4000],
        }
        existing = self.browse()
        if zid:
            existing = self.search([('zernio_id', '=', zid)], limit=1)
        if not existing and ad_account:
            existing = self.search([
                ('ad_account_id', '=', ad_account.id),
                ('keyword', '=', text),
                ('adset_id_remote', '=', vals['adset_id_remote'] or False),
                ('match_type', '=', vals['match_type']),
                ('negative', '=', vals['negative']),
            ], limit=1)
        if existing:
            existing.write(vals)
            return existing
        return self.create(vals)

    @api.model
    def action_sync_from_zernio(self):
        """Pull Google Search keywords for all googleads connections."""
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        socials = self.env['tcrm.marketing.account'].search([
            ('platform', '=', 'googleads'),
            ('active', '=', True),
            ('status', '=', 'connected'),
        ])
        synced = 0
        errors = []
        Keyword = self.sudo()
        for social in socials:
            ad_accounts = self.env['tcrm.marketing.ad.account'].search([
                ('account_id', '=', social.id),
                ('active', '=', True),
            ])
            if not ad_accounts:
                ad_accounts = self.env['tcrm.marketing.ad.account'].browse()
            targets = ad_accounts or [False]
            for ad_acc in targets:
                page = 1
                while page <= 40:
                    try:
                        data = client.list_keywords(
                            page=page,
                            limit=100,
                            account_id=social.zernio_id,
                            ad_account_id=ad_acc.meta_act_id if ad_acc else None,
                        )
                    except ZernioError as exc:
                        errors.append(f'{social.name}: {exc}')
                        break
                    rows = data.get('keywords') or []
                    for item in rows:
                        Keyword._upsert_from_remote(item, social=social, ad_account=ad_acc)
                        synced += 1
                    pagination = data.get('pagination') or {}
                    total_pages = int(pagination.get('pages') or 1)
                    if page >= total_pages or not rows:
                        break
                    page += 1

        msg = _('%s Google anahtar kelime senkronize edildi.') % synced
        if errors:
            msg = _('%s kelime senkronize edildi. Hatalar: %s') % (synced, '; '.join(errors[:3]))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Marketing Hub'),
                'message': msg,
                'type': 'success' if synced else 'warning',
                'sticky': bool(errors),
            },
        }
