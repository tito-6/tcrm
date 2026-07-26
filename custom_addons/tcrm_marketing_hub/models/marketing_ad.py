# -*- coding: utf-8 -*-
import json
import logging
import re

from tcrm import _, api, fields, models
from tcrm.exceptions import UserError

from ..services.zernio_client import ZernioError

_logger = logging.getLogger(__name__)


def detect_placement_platform(
    *,
    name: str = '',
    campaign_name: str = '',
    creative: dict | None = None,
    explicit: str | None = None,
) -> str:
    """Infer Facebook / Instagram / Meta placement from names + creative signals.

    Meta ads often carry both FB story IDs and IG media IDs even when the
    placement is mixed — so creative IG fields alone must not force Instagram.
    Prefer explicit naming; otherwise return ``meta``.
    """
    if explicit in ('instagram', 'facebook', 'meta'):
        return explicit
    text = f'{name or ""} {campaign_name or ""}'.lower()
    creative = creative or {}
    has_ig = bool(
        creative.get('instagramPermalinkUrl')
        or creative.get('effectiveInstagramMediaId')
        or creative.get('instagramUserId')
    )
    has_fb = bool(creative.get('effectiveObjectStoryId'))
    mentions_ig = bool(re.search(r'\b(instagram|insta|\big\b)', text))
    mentions_fb = bool(re.search(r'\b(facebook|\bfb\b)', text))
    is_story = 'story' in text or 'stories' in text

    if mentions_ig and mentions_fb:
        return 'meta'
    if mentions_ig:
        return 'instagram'
    if mentions_fb:
        return 'facebook'
    # Stories with IG creative are almost always Instagram placements
    if is_story and has_ig:
        return 'instagram'
    # Pure FB page post creative (no IG media) → Facebook
    if has_fb and not has_ig:
        return 'facebook'
    # Unknown / Advantage+ / mixed → Meta (never silently label as Facebook)
    return 'meta'


class MarketingAdAccount(models.Model):
    _name = 'tcrm.marketing.ad.account'
    _description = 'Meta Reklam Hesabı'
    _order = 'name'

    name = fields.Char(string='Ad', required=True)
    meta_act_id = fields.Char(string='Meta Ad Account ID', required=True, index=True)
    currency = fields.Char(string='Para Birimi')
    business_name = fields.Char(string='İşletme Adı')
    timezone_name = fields.Char(string='Saat Dilimi')
    minimum_daily_budget = fields.Float(string='Min. Günlük Bütçe')
    selectable = fields.Boolean(string='Seçilebilir', default=True)
    account_id = fields.Many2one(
        'tcrm.marketing.account',
        string='Sosyal Hesap',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(related='account_id.company_id', store=True, readonly=True)
    last_sync_at = fields.Datetime(string='Son Senkron')
    active = fields.Boolean(default=True)
    campaign_count = fields.Integer(compute='_compute_campaign_count')

    _sql_constraints = [
        ('meta_act_social_uniq', 'unique(meta_act_id, account_id)', 'Bu reklam hesabı zaten kayıtlı.'),
    ]

    def _compute_campaign_count(self):
        Campaign = self.env['tcrm.marketing.campaign']
        for rec in self:
            rec.campaign_count = Campaign.search_count([('ad_account_id', '=', rec.id)])

    def action_sync_from_zernio(self):
        """Sync Meta ad accounts from Zernio (callable from list header buttons)."""
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        accounts = self.env['tcrm.marketing.account'].search([
            ('platform', 'in', ('facebook', 'instagram')),
            ('active', '=', True),
        ])
        synced = 0
        for social in accounts:
            try:
                rows = client.list_ad_accounts(social.zernio_id)
            except ZernioError:
                continue
            for item in rows:
                act_id = item.get('id') or item.get('accountId')
                if not act_id:
                    continue
                vals = {
                    'name': item.get('name') or act_id,
                    'meta_act_id': act_id,
                    'currency': item.get('currency') or False,
                    'business_name': item.get('businessName') or False,
                    'timezone_name': item.get('timezoneName') or False,
                    'minimum_daily_budget': float(item.get('minimumDailyBudget') or 0),
                    'selectable': bool(item.get('selectable', True)),
                    'account_id': social.id,
                    'last_sync_at': fields.Datetime.now(),
                    'active': True,
                }
                existing = self.sudo().search([
                    ('meta_act_id', '=', act_id),
                    ('account_id', '=', social.id),
                ], limit=1)
                if existing:
                    existing.write(vals)
                else:
                    self.sudo().create(vals)
                synced += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Marketing Hub'),
                'message': _('%s Meta reklam hesabı senkronize edildi.') % synced,
                'type': 'success',
                'sticky': False,
            },
        }


def extract_creative_preview(creative):
    """Normalize Meta/Zernio creative blob for UI preview (image / video / reel).

    Zernio creative shape (docs.zernio.com get-ad):
      thumbnailUrl, imageUrl, videoId, videoUrl, mediaUrls[],
      instagramPermalinkUrl, effectiveInstagramMediaId, effectiveObjectStoryId, body, linkUrl
    Tree sync often returns IDs/permalink only — callers should refresh via get_ad.
    """
    empty = {
        'media_type': 'none',
        'image_url': '',
        'thumbnail_url': '',
        'video_url': '',
        'video_id': '',
        'body': '',
        'title': '',
        'link_url': '',
        'permalink': '',
        'media_urls': [],
        'needs_refresh': False,
    }
    if not creative:
        return empty
    if isinstance(creative, str):
        try:
            creative = json.loads(creative)
        except Exception:
            creative = {}
    creative = creative or {}
    media_urls = (
        creative.get('mediaUrls')
        or creative.get('media_urls')
        or creative.get('images')
        or []
    )
    if isinstance(media_urls, str):
        media_urls = [media_urls]
    # Flatten nested {url: ...} objects from some Meta payloads
    flat_urls = []
    for item in media_urls:
        if isinstance(item, dict):
            flat_urls.append(item.get('url') or item.get('src') or item.get('imageUrl') or '')
        else:
            flat_urls.append(str(item or ''))
    media_urls = [u for u in flat_urls if u]

    image_url = (
        creative.get('imageUrl')
        or creative.get('image_url')
        or creative.get('picture')
        or creative.get('image_hash_url')
        or creative.get('pinterestImageUrl')
        or (media_urls[0] if media_urls else '')
        or ''
    )
    thumbnail_url = (
        creative.get('thumbnailUrl')
        or creative.get('thumbnail_url')
        or creative.get('image_url')
        or image_url
        or ''
    )
    video_id = str(
        creative.get('videoId')
        or creative.get('video_id')
        or creative.get('video_source_id')
        or ''
    )
    video_url = (
        creative.get('videoUrl')
        or creative.get('video_url')
        or creative.get('video_src')
        or ''
    )
    if video_id and not video_url:
        video_url = f'https://www.facebook.com/watch/?v={video_id}'
    permalink = (
        creative.get('instagramPermalinkUrl')
        or creative.get('instagram_permalink_url')
        or creative.get('permalink_url')
        or creative.get('permalink')
        or ''
    )
    object_type = str(creative.get('objectType') or creative.get('object_type') or '').lower()
    ig_media_id = str(
        creative.get('effectiveInstagramMediaId')
        or creative.get('effective_instagram_media_id')
        or ''
    )
    story_id = str(
        creative.get('effectiveObjectStoryId')
        or creative.get('effective_object_story_id')
        or creative.get('objectStoryId')
        or ''
    )

    if video_id or video_url or 'video' in object_type or 'reel' in object_type:
        media_type = 'video'
    elif image_url or thumbnail_url:
        media_type = 'image'
    elif permalink or ig_media_id or story_id:
        # Have Meta/IG references but no direct media URL yet — UI can deep-link;
        # caller should refresh via GET /v1/ads/{platformAdId}.
        media_type = 'link'
    else:
        media_type = 'none'

    needs_refresh = media_type in ('none', 'link') and bool(ig_media_id or story_id or permalink)

    return {
        'media_type': media_type,
        'image_url': image_url or '',
        'thumbnail_url': thumbnail_url or '',
        'video_url': video_url or '',
        'video_id': video_id,
        'body': (creative.get('body') or creative.get('message') or creative.get('googleDescription') or '')[:2000],
        'title': (creative.get('title') or creative.get('name') or creative.get('googleHeadline') or '')[:500],
        'link_url': creative.get('linkUrl') or creative.get('link_url') or '',
        'permalink': permalink,
        'media_urls': media_urls[:8],
        'needs_refresh': needs_refresh,
        'ig_media_id': ig_media_id,
        'story_id': story_id,
    }


class MarketingMetaAd(models.Model):
    """Cached Meta ads for lead-source resolution and monitoring."""

    _name = 'tcrm.marketing.meta.ad'
    _description = 'Meta Reklam (önbellek)'
    _order = 'write_date desc'

    name = fields.Char(string='Reklam Adı', required=True)
    platform_ad_id = fields.Char(string='Meta Ad ID', required=True, index=True)
    zernio_id = fields.Char(string='Zernio Ad ID', index=True)
    source_platform = fields.Selection(
        [
            ('facebook', 'Facebook'),
            ('instagram', 'Instagram'),
            ('meta', 'Meta (Facebook + Instagram)'),
        ],
        string='Kaynak Platform',
        default='meta',
        index=True,
    )
    status = fields.Char(string='Durum')
    campaign_id = fields.Many2one('tcrm.marketing.campaign', string='Kampanya', ondelete='cascade')
    ad_account_id = fields.Many2one('tcrm.marketing.ad.account', string='Reklam Hesabı', ondelete='set null')
    account_id = fields.Many2one('tcrm.marketing.account', string='Sosyal Hesap', ondelete='set null')
    company_id = fields.Many2one('res.company', string='Şirket', required=True, default=lambda s: s.env.company)
    creative_json = fields.Text(groups='tcrm_marketing_hub.group_marketing_admin')
    last_sync_at = fields.Datetime(string='Son Senkron')

    _platform_ad_uniq = models.Constraint(
        'unique(platform_ad_id)',
        'Bu Meta reklam zaten kayıtlı.',
    )

    def get_creative_preview(self):
        self.ensure_one()
        return extract_creative_preview(self.creative_json)

    def action_refresh_creative_from_zernio(self):
        """Fetch full creative (image/video URLs) via GET /v1/ads/{adId}.

        Tree sync often stores only IG media IDs / permalink. get_ad accepts
        Zernio _id OR Meta platformAdId (docs.zernio.com get-ad).
        """
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
        except Exception as exc:
            _logger.warning('Creative refresh: no Zernio client (%s)', exc)
            return False
        refreshed = 0
        for ad in self:
            keys = [ad.zernio_id, ad.platform_ad_id]
            remote = {}
            for key in keys:
                if not key:
                    continue
                try:
                    remote = client.get_ad(str(key)) or {}
                except Exception as exc:
                    _logger.debug('get_ad(%s) failed: %s', key, exc)
                    remote = {}
                if remote.get('creative'):
                    break
            creative = remote.get('creative') or {}
            if not creative:
                continue
            preview = extract_creative_preview(creative)
            ad.write({
                'creative_json': json.dumps(creative, ensure_ascii=False, default=str)[:8000],
                'name': remote.get('name') or ad.name,
                'zernio_id': str(remote.get('_id') or ad.zernio_id or '') or ad.zernio_id,
                'last_sync_at': fields.Datetime.now(),
            })
            if preview.get('media_type') in ('image', 'video', 'link'):
                refreshed += 1
        return refreshed


class MarketingCampaign(models.Model):
    _name = 'tcrm.marketing.campaign'
    _description = 'Meta Reklam Kampanyası'
    _order = 'write_date desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Kampanya Adı', required=True, tracking=True)
    zernio_id = fields.Char(string='Kampanya ID', index=True, copy=False)
    platform_campaign_id = fields.Char(string='Meta Kampanya ID', index=True)
    platform = fields.Selection(
        [
            ('facebook', 'Facebook'),
            ('instagram', 'Instagram'),
            ('meta', 'Meta (Facebook + Instagram)'),
        ],
        string='Platform',
        default='meta',
        tracking=True,
    )
    status = fields.Selection(
        [
            ('active', 'Aktif'),
            ('paused', 'Duraklatıldı'),
            ('pending_review', 'İncelemede'),
            ('deleted', 'Silindi'),
            ('unknown', 'Bilinmiyor'),
        ],
        string='Durum',
        default='unknown',
        tracking=True,
    )
    review_status = fields.Char(string='İnceleme Durumu')
    budget_level = fields.Selection(
        [('campaign', 'Kampanya (CBO)'), ('adset', 'Reklam Seti (ABO)')],
        string='Bütçe Seviyesi',
    )
    budget_amount = fields.Float(string='Bütçe')
    budget_type = fields.Char(string='Bütçe Tipi')
    currency = fields.Char(string='Para Birimi')
    spend = fields.Float(string='Harcama')
    impressions = fields.Float(string='Gösterim')
    clicks = fields.Float(string='Tıklama')
    conversions = fields.Float(string='Dönüşüm')
    purchase_value = fields.Float(string='Satın Alma Değeri')
    roas = fields.Float(string='ROAS')
    account_id = fields.Many2one('tcrm.marketing.account', string='Sosyal Hesap', ondelete='set null')
    ad_account_id = fields.Many2one('tcrm.marketing.ad.account', string='Reklam Hesabı', ondelete='set null', index=True)
    company_id = fields.Many2one(
        'res.company',
        string='Şirket',
        required=True,
        default=lambda self: self.env.company,
    )
    last_sync_at = fields.Datetime(string='Son Senkron')
    raw_json = fields.Text(groups='tcrm_marketing_hub.group_marketing_admin')
    meta_ad_ids = fields.One2many('tcrm.marketing.meta.ad', 'campaign_id', string='Reklamlar')

    @api.model
    def _map_status(self, value):
        if not value:
            return 'unknown'
        value = str(value).lower().replace(' ', '_')
        mapping = {
            'active': 'active',
            'paused': 'paused',
            'pending_review': 'pending_review',
            'in_review': 'pending_review',
            'deleted': 'deleted',
            'archived': 'deleted',
            'cancelled': 'deleted',
        }
        return mapping.get(value, 'unknown')

    @api.model
    def _ensure_meta_ads_connected(self, client):
        """Best-effort: connect/scope Meta Ads for each Facebook page."""
        Profile = self.env['tcrm.marketing.profile']
        profiles = Profile.search([('active', '=', True)])
        for profile in profiles:
            socials = self.env['tcrm.marketing.account'].search([
                ('platform', '=', 'facebook'),
                ('profile_id', '=', profile.id),
                ('active', '=', True),
            ])
            if not socials:
                socials = self.env['tcrm.marketing.account'].search([
                    ('platform', '=', 'facebook'),
                    ('active', '=', True),
                ], limit=1)
            for social in socials:
                acts = self.env['tcrm.marketing.ad.account'].search([
                    ('account_id', '=', social.id),
                    ('active', '=', True),
                ])
                act_ids = acts.mapped('meta_act_id')
                try:
                    client.connect_facebook_ads(
                        profile_id=profile.zernio_id,
                        account_id=social.zernio_id,
                        ad_account_ids=act_ids or None,
                    )
                except ZernioError as exc:
                    # Retry without unreachable acts — connect with no scope list
                    _logger.info('Scoped Meta Ads connect failed (%s); retrying bare connect', exc)
                    try:
                        client.connect_facebook_ads(
                            profile_id=profile.zernio_id,
                            account_id=social.zernio_id,
                        )
                    except ZernioError as exc2:
                        _logger.warning('Meta Ads connect failed: %s', exc2)

    @api.model
    def _upsert_campaign_from_tree(self, item, *, ad_account, social_account):
        zid = item.get('_id') or item.get('id') or item.get('platformCampaignId')
        if not zid:
            return self.browse(), []
        camp_name = (
            item.get('campaignName')
            or item.get('name')
            or f'Kampanya {zid}'
        )
        metrics = item.get('metrics') or {}
        budget = item.get('campaignBudget') or item.get('budget') or {}
        ad_platforms = []
        for aset in item.get('adSets') or []:
            for ad in aset.get('ads') or []:
                ad_platforms.append(
                    detect_placement_platform(
                        name=ad.get('name') or '',
                        campaign_name=camp_name,
                        creative=ad.get('creative') or {},
                    )
                )
        if not ad_platforms:
            platform = detect_placement_platform(name=camp_name, campaign_name=camp_name)
        else:
            unique = set(ad_platforms)
            if unique == {'instagram'}:
                platform = 'instagram'
            elif unique == {'facebook'}:
                platform = 'facebook'
            else:
                platform = 'meta'

        vals = {
            'name': camp_name,
            'zernio_id': str(zid),
            'platform_campaign_id': str(item.get('platformCampaignId') or zid),
            'platform': platform,
            'status': self._map_status(item.get('status') or item.get('platformCampaignStatus')),
            'review_status': item.get('reviewStatus') or False,
            'budget_level': item.get('budgetLevel') or False,
            'budget_amount': float((budget or {}).get('amount') or item.get('budgetAmount') or 0),
            'budget_type': (budget or {}).get('type') or item.get('budgetType') or False,
            'currency': item.get('currency') or ad_account.currency or False,
            'spend': float(metrics.get('spend') or 0),
            'impressions': float(metrics.get('impressions') or 0),
            'clicks': float(metrics.get('clicks') or metrics.get('linkClicks') or 0),
            'conversions': float(metrics.get('conversions') or 0),
            'purchase_value': float(metrics.get('purchaseValue') or 0),
            'roas': float(metrics.get('roas') or 0),
            'account_id': social_account.id if social_account else False,
            'ad_account_id': ad_account.id if ad_account else False,
            'company_id': (ad_account.company_id.id if ad_account else self.env.company.id),
            'last_sync_at': fields.Datetime.now(),
            'raw_json': json.dumps(item, ensure_ascii=False, default=str)[:12000],
        }
        existing = self.sudo().search([
            '|',
            ('zernio_id', '=', str(zid)),
            ('platform_campaign_id', '=', str(item.get('platformCampaignId') or zid)),
        ], limit=1)
        if existing:
            existing.write(vals)
            campaign = existing
        else:
            campaign = self.sudo().create(vals)

        MetaAd = self.env['tcrm.marketing.meta.ad'].sudo()
        ads_out = []
        for aset in item.get('adSets') or []:
            aset_name = aset.get('adSetName') or aset.get('name') or ''
            for ad in aset.get('ads') or []:
                pad = ad.get('platformAdId') or ad.get('id') or ad.get('_id')
                if not pad:
                    continue
                creative = ad.get('creative') or {}
                ad_name = ad.get('name') or ad.get('adName') or f'Reklam {pad}'
                src = detect_placement_platform(
                    name=f'{ad_name} {aset_name}',
                    campaign_name=camp_name,
                    creative=creative,
                )
                ad_vals = {
                    'name': ad_name,
                    'platform_ad_id': str(pad),
                    'zernio_id': str(ad.get('_id') or '') or False,
                    'source_platform': src,
                    'status': ad.get('status') or False,
                    'campaign_id': campaign.id,
                    'ad_account_id': ad_account.id if ad_account else False,
                    'account_id': social_account.id if social_account else False,
                    'company_id': campaign.company_id.id,
                    'creative_json': json.dumps(creative, ensure_ascii=False, default=str)[:8000],
                    'last_sync_at': fields.Datetime.now(),
                }
                found = MetaAd.search([('platform_ad_id', '=', str(pad))], limit=1)
                if found:
                    found.write(ad_vals)
                    ads_out.append(found)
                else:
                    ads_out.append(MetaAd.create(ad_vals))
        return campaign, ads_out

    def action_sync_from_zernio(self):
        """Sync campaigns from Zernio/Meta.

        Not @api.model: list-header object buttons pass a recordset as self.
        """
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        # Refresh ad accounts then connect Meta Ads scope
        try:
            self.env['tcrm.marketing.ad.account'].action_sync_from_zernio()
        except Exception as exc:
            _logger.warning('Ad account sync before campaigns failed: %s', exc)

        self._ensure_meta_ads_connected(client)

        ad_accounts = self.env['tcrm.marketing.ad.account'].search([('active', '=', True)])
        if not ad_accounts:
            raise UserError(_(
                'Önce Meta reklam hesabı bağlayın / senkronize edin '
                '(Marketing Hub → Reklam Hesapları).'
            ))

        synced = 0
        errors = []
        for ad_acc in ad_accounts:
            page = 1
            while page <= 40:
                try:
                    tree = client.get_ads_tree(
                        page=page,
                        limit=50,
                        source='all',
                        ad_account_id=ad_acc.meta_act_id,
                        date_from='2020-01-01',
                        date_to=fields.Date.today().isoformat(),
                    )
                except ZernioError as exc:
                    errors.append(f'{ad_acc.name}: {exc}')
                    _logger.warning('Campaign tree failed for %s: %s', ad_acc.meta_act_id, exc)
                    break
                campaigns = tree.get('campaigns') or []
                for item in campaigns:
                    self._upsert_campaign_from_tree(
                        item,
                        ad_account=ad_acc,
                        social_account=ad_acc.account_id,
                    )
                    synced += 1
                pagination = tree.get('pagination') or {}
                total_pages = int(pagination.get('pages') or 1)
                if page >= total_pages or not campaigns:
                    break
                page += 1

        msg = _('%s kampanya tüm reklam hesaplarından senkronize edildi.') % synced
        if errors:
            msg = _('%s kampanya senkronize edildi. Bazı hesaplar atlandı: %s') % (
                synced,
                '; '.join(errors[:3]),
            )
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

    def action_pause(self):
        return self._set_remote_status('paused')

    def action_activate(self):
        return self._set_remote_status('active')

    def _set_remote_status(self, status):
        self.ensure_one()
        cid = self.platform_campaign_id or self.zernio_id
        if not cid:
            raise UserError(_('Kampanya ID yok.'))
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
            client.update_campaign_status(cid, status=status, platform='facebook')
        except ZernioError as exc:
            raise UserError(str(exc)) from exc
        self.status = status
        return True

    def action_duplicate(self):
        self.ensure_one()
        cid = self.platform_campaign_id or self.zernio_id
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
            client.duplicate_campaign(cid, platform='facebook')
        except ZernioError as exc:
            raise UserError(str(exc)) from exc
        self.env['tcrm.marketing.campaign'].action_sync_from_zernio()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Marketing Hub'),
                'message': _('Kampanya kopyalandı (duraklatılmış).'),
                'type': 'success',
                'sticky': False,
            },
        }
