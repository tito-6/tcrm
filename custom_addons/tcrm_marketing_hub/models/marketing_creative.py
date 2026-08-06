# -*- coding: utf-8 -*-
"""Creative asset library (Meta images/videos/reels + Google IMAGE/YOUTUBE assets)."""
from __future__ import annotations

import json
import logging
import time

from tcrm import _, api, fields, models
from tcrm.exceptions import UserError

from ..services.zernio_client import ZernioError

_logger = logging.getLogger(__name__)

GOOGLE_ASSET_GAQL = (
    "SELECT campaign.id, campaign.name, asset.id, asset.name, asset.type, "
    "asset.image_asset.full_size.url, asset.youtube_video_asset.youtube_video_id, "
    "asset.youtube_video_asset.youtube_video_title "
    "FROM campaign_asset"
)


class MarketingCreative(models.Model):
    _name = 'tcrm.marketing.creative'
    _description = 'Reklam Kreatif / Medya Varlığı'
    _order = 'write_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Ad', required=True)
    provider = fields.Selection(
        [('meta', 'Meta'), ('google', 'Google Ads')],
        string='Sağlayıcı',
        required=True,
        index=True,
        default='meta',
    )
    media_type = fields.Selection(
        [
            ('image', 'Görsel'),
            ('video', 'Video / Reel'),
            ('text', 'Metin'),
            ('other', 'Diğer'),
        ],
        string='Medya Tipi',
        default='image',
        index=True,
    )
    platform_creative_id = fields.Char(string='Platform Kreatif ID', index=True)
    image_url = fields.Char(string='Görsel URL')
    thumbnail_url = fields.Char(string='Önizleme URL')
    video_url = fields.Char(string='Video URL')
    video_id = fields.Char(string='Video ID')
    permalink = fields.Char(string='Bağlantı')
    body = fields.Text(string='Metin')
    status = fields.Char(string='Durum')
    campaign_name = fields.Char(string='Kampanya')
    campaign_id_remote = fields.Char(string='Kampanya ID', index=True)
    ad_account_id = fields.Many2one(
        'tcrm.marketing.ad.account',
        string='Reklam Hesabı',
        ondelete='set null',
        index=True,
    )
    account_id = fields.Many2one(
        'tcrm.marketing.account',
        string='Bağlantı',
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
    last_sync_at = fields.Datetime(string='Son Senkron')
    raw_json = fields.Text(groups='tcrm_marketing_hub.group_marketing_admin')

    _sql_constraints = [
        (
            'platform_creative_provider_uniq',
            'unique(provider, platform_creative_id, company_id)',
            'Bu kreatif zaten kayıtlı.',
        ),
    ]

    @api.model
    def _upsert(self, vals):
        pid = vals.get('platform_creative_id')
        provider = vals.get('provider') or 'meta'
        company_id = vals.get('company_id') or self.env.company.id
        existing = self.browse()
        if pid:
            existing = self.search([
                ('platform_creative_id', '=', str(pid)),
                ('provider', '=', provider),
                ('company_id', '=', company_id),
            ], limit=1)
        if existing:
            existing.write(vals)
            return existing
        return self.create(vals)

    @api.model
    def action_sync_meta_library(self):
        """Pull Meta ad account creatives + images libraries via Zernio."""
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        socials = self.env['tcrm.marketing.account'].search([
            ('platform', '=', 'metaads'),
            ('active', '=', True),
            ('company_id', '=', self.env.company.id),
        ])
        if not socials:
            socials = self.env['tcrm.marketing.account'].search([
                ('platform', 'in', ('facebook', 'instagram')),
                ('active', '=', True),
                ('company_id', '=', self.env.company.id),
            ], limit=1)

        synced = 0
        seen_acts = set()
        for social in socials:
            ad_accs = self.env['tcrm.marketing.ad.account'].search([
                ('account_id', '=', social.id),
                ('provider', '=', 'meta'),
                ('active', '=', True),
            ])
            # Fall back: any meta provider act linked to company under this social's acts list
            if not ad_accs:
                continue
            for ad_acc in ad_accs:
                act = ad_acc.meta_act_id
                if not act or act in seen_acts:
                    continue
                seen_acts.add(act)

                # Creatives library (videos/reels/images)
                after = None
                for _ in range(20):
                    try:
                        data = client.list_ad_creatives(
                            account_id=social.zernio_id,
                            ad_account_id=act,
                            limit=50,
                        )
                    except ZernioError as exc:
                        _logger.warning('list_ad_creatives %s: %s', act, exc)
                        break
                    # Zernio may return {data: [...], paging} or {creatives: [...]}
                    rows = data.get('data') or data.get('creatives') or []
                    for item in rows:
                        cid = str(item.get('id') or item.get('creative_id') or '')
                        if not cid:
                            continue
                        obj = str(item.get('object_type') or item.get('objectType') or '').upper()
                        media = 'video' if 'VIDEO' in obj or 'REEL' in obj else 'image'
                        thumb = (
                            item.get('thumbnail_url')
                            or item.get('thumbnailUrl')
                            or item.get('image_url')
                            or item.get('imageUrl')
                            or ''
                        )
                        self._upsert({
                            'name': (item.get('name') or f'Meta kreatif {cid}')[:200],
                            'provider': 'meta',
                            'media_type': media,
                            'platform_creative_id': cid,
                            'thumbnail_url': thumb or False,
                            'image_url': item.get('image_url') or item.get('imageUrl') or thumb or False,
                            'video_id': item.get('video_id') or item.get('videoId') or False,
                            'status': item.get('status') or False,
                            'ad_account_id': ad_acc.id,
                            'account_id': social.id,
                            'company_id': self.env.company.id,
                            'last_sync_at': fields.Datetime.now(),
                            'raw_json': json.dumps(item, ensure_ascii=False, default=str)[:6000],
                        })
                        synced += 1
                    paging = data.get('paging') or {}
                    after = (paging.get('cursors') or {}).get('after') or paging.get('after')
                    if not after or not rows:
                        break
                    time.sleep(0.4)

                # Image library
                try:
                    data = client.list_ad_images(
                        account_id=social.zernio_id,
                        ad_account_id=act,
                        limit=50,
                    )
                except ZernioError as exc:
                    _logger.warning('list_ad_images %s: %s', act, exc)
                    data = {}
                rows = data.get('images') or data.get('data') or []
                for item in rows:
                    hid = str(item.get('hash') or item.get('id') or '')
                    url = item.get('url') or item.get('permalink_url') or ''
                    if not hid or not url:
                        continue
                    self._upsert({
                        'name': (item.get('name') or f'Meta görsel {hid[:12]}')[:200],
                        'provider': 'meta',
                        'media_type': 'image',
                        'platform_creative_id': f'img:{hid}',
                        'image_url': url,
                        'thumbnail_url': url,
                        'ad_account_id': ad_acc.id,
                        'account_id': social.id,
                        'company_id': self.env.company.id,
                        'last_sync_at': fields.Datetime.now(),
                        'raw_json': json.dumps(item, ensure_ascii=False, default=str)[:4000],
                    })
                    synced += 1
                time.sleep(0.4)

        return synced

    @api.model
    def action_sync_google_assets(self):
        """Pull Google IMAGE / YOUTUBE assets via Zernio GAQL insights."""
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        socials = self.env['tcrm.marketing.account'].search([
            ('platform', '=', 'googleads'),
            ('active', '=', True),
            ('company_id', '=', self.env.company.id),
        ])
        synced = 0
        for social in socials:
            ad_accs = self.env['tcrm.marketing.ad.account'].search([
                ('account_id', '=', social.id),
                ('provider', '=', 'google'),
                ('active', '=', True),
            ])
            for ad_acc in ad_accs:
                try:
                    raw = client.query_ad_insights(
                        account_id=social.zernio_id,
                        query=GOOGLE_ASSET_GAQL,
                        customer_id=ad_acc.meta_act_id,
                    )
                except ZernioError as exc:
                    _logger.warning('Google asset GAQL %s: %s', ad_acc.meta_act_id, exc)
                    continue
                for row in (raw.get('data') or []):
                    asset = row.get('asset') or {}
                    camp = row.get('campaign') or {}
                    atype = str(asset.get('type') or '').upper()
                    aid = str(asset.get('id') or '')
                    if not aid:
                        # parse from resourceName customers/X/assets/ID
                        rn = str(asset.get('resourceName') or '')
                        if '/assets/' in rn:
                            aid = rn.rsplit('/assets/', 1)[-1]
                    if not aid:
                        continue
                    image_url = ''
                    video_id = ''
                    video_url = ''
                    media = 'other'
                    yta = {}
                    if atype == 'IMAGE' or asset.get('imageAsset'):
                        media = 'image'
                        image_asset = asset.get('imageAsset') or asset.get('image_asset') or {}
                        full = image_asset.get('fullSize') or image_asset.get('full_size') or {}
                        image_url = full.get('url') or image_asset.get('url') or ''
                    elif 'YOUTUBE' in atype or asset.get('youtubeVideoAsset'):
                        media = 'video'
                        yta = asset.get('youtubeVideoAsset') or asset.get('youtube_video_asset') or {}
                        video_id = str(yta.get('youtubeVideoId') or yta.get('youtube_video_id') or '')
                        if video_id:
                            video_url = f'https://www.youtube.com/watch?v={video_id}'
                            image_url = f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'
                    else:
                        continue  # skip snippets/sitelines etc.
                    if not (image_url or video_url):
                        continue
                    self._upsert({
                        'name': (
                            asset.get('name')
                            or (yta.get('youtubeVideoTitle') if media == 'video' else None)
                            or camp.get('name')
                            or f'Google asset {aid}'
                        )[:200],
                        'provider': 'google',
                        'media_type': media,
                        'platform_creative_id': f'gasset:{aid}',
                        'image_url': image_url or False,
                        'thumbnail_url': image_url or False,
                        'video_url': video_url or False,
                        'video_id': video_id or False,
                        'campaign_name': camp.get('name') or False,
                        'campaign_id_remote': str(camp.get('id') or '') or False,
                        'ad_account_id': ad_acc.id,
                        'account_id': social.id,
                        'company_id': self.env.company.id,
                        'last_sync_at': fields.Datetime.now(),
                        'raw_json': json.dumps(row, ensure_ascii=False, default=str)[:6000],
                    })
                    synced += 1
                    # Also stamp matching Google ads/campaigns with first image if empty
                    if image_url and camp.get('id'):
                        MetaAd = self.env['tcrm.marketing.meta.ad'].sudo()
                        thin = MetaAd.search([
                            ('source_platform', '=', 'google'),
                            ('campaign_id.platform_campaign_id', '=', str(camp.get('id'))),
                            '|',
                            ('creative_image_url', '=', False),
                            ('creative_media_type', 'in', ('none', 'text', False)),
                        ], limit=20)
                        for ad in thin:
                            creative = {}
                            try:
                                creative = json.loads(ad.creative_json or '{}')
                            except Exception:
                                creative = {}
                            creative.setdefault('mediaUrls', [])
                            if image_url not in creative['mediaUrls']:
                                creative['mediaUrls'] = [image_url] + list(creative.get('mediaUrls') or [])
                            if video_url:
                                creative['videoUrl'] = video_url
                                creative['videoId'] = video_id
                            creative['imageUrl'] = creative.get('imageUrl') or image_url
                            creative['thumbnailUrl'] = creative.get('thumbnailUrl') or image_url
                            ad.write({
                                'creative_json': json.dumps(creative, ensure_ascii=False, default=str)[:8000],
                            })
        return synced

    @api.model
    def action_sync_all_creatives(self):
        meta_n = self.action_sync_meta_library()
        google_n = self.action_sync_google_assets()
        # Refresh thin ad creatives from get_ad
        try:
            ad_n = self.env['tcrm.marketing.meta.ad'].action_refresh_all_creatives(limit=150)
        except Exception as exc:
            _logger.warning('ad creative refresh: %s', exc)
            ad_n = 0
        return {
            'meta_library': meta_n,
            'google_assets': google_n,
            'ads_refreshed': ad_n,
        }
