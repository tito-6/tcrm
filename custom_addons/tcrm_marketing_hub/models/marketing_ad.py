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
    if explicit in ('instagram', 'facebook', 'meta', 'google'):
        return explicit
    text = f'{name or ""} {campaign_name or ""}'.lower()
    creative = creative or {}
    if (
        creative.get('googleHeadline')
        or creative.get('googleHeadlines')
        or creative.get('googleDescription')
        or creative.get('googleDescriptions')
    ):
        return 'google'
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
    _description = 'Reklam Hesabı (Meta / Google)'
    _order = 'provider, name'

    name = fields.Char(string='Ad', required=True)
    meta_act_id = fields.Char(
        string='Platform Hesap ID',
        required=True,
        index=True,
        help='Meta: act_… · Google Ads: müşteri numarası (customer id)',
    )
    provider = fields.Selection(
        [
            ('meta', 'Meta'),
            ('google', 'Google Ads'),
        ],
        string='Sağlayıcı',
        default='meta',
        required=True,
        index=True,
    )
    currency = fields.Char(string='Para Birimi')
    business_name = fields.Char(string='İşletme Adı')
    timezone_name = fields.Char(string='Saat Dilimi')
    minimum_daily_budget = fields.Float(string='Min. Günlük Bütçe')
    selectable = fields.Boolean(string='Seçilebilir', default=True)
    account_status = fields.Char(string='Hesap Durumu')
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

    @api.model
    def _provider_for_social(self, social):
        if social.platform == 'googleads':
            return 'google'
        return 'meta'

    def action_sync_from_zernio(self):
        """Sync Meta + Google ad accounts from Zernio."""
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        accounts = self.env['tcrm.marketing.account'].search([
            ('platform', 'in', ('facebook', 'instagram', 'googleads', 'metaads')),
            ('active', '=', True),
        ])
        synced = 0
        for social in accounts:
            try:
                rows = client.list_ad_accounts(social.zernio_id)
            except ZernioError:
                continue
            provider = self._provider_for_social(social)
            for item in rows:
                act_id = item.get('id') or item.get('accountId') or item.get('customerId')
                if not act_id:
                    continue
                vals = {
                    'name': item.get('name') or act_id,
                    'meta_act_id': str(act_id),
                    'provider': provider,
                    'currency': item.get('currency') or False,
                    'business_name': item.get('businessName') or False,
                    'timezone_name': item.get('timezoneName') or False,
                    'minimum_daily_budget': float(item.get('minimumDailyBudget') or 0),
                    'selectable': bool(item.get('selectable', True)),
                    'account_status': str(
                        item.get('accountStatus') or item.get('status') or ''
                    ) or False,
                    'account_id': social.id,
                    'last_sync_at': fields.Datetime.now(),
                    'active': True,
                }
                existing = self.sudo().search([
                    ('meta_act_id', '=', str(act_id)),
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
                'message': _('%s reklam hesabı senkronize edildi.') % synced,
                'type': 'success',
                'sticky': False,
            },
        }


def prefer_display_image_url(image_url, thumbnail_url=''):
    """Pick a browser-renderable creative image URL.

    Prefer Meta CDN hosts (fbcdn / scontent / cdninstagram). The
    ``facebook.com/ads/image/?d=...`` proxy often fails in the CRM UI even
    when a real CDN ``imageUrl`` is available.
    """
    candidates = [u for u in (image_url, thumbnail_url) if u]
    if not candidates:
        return ''

    def _score(url):
        u = (url or '').lower()
        if any(h in u for h in (
            'fbcdn.net', 'scontent', 'cdninstagram.com', 'instagram.com/static',
            'googleusercontent.com', 'ggpht.com', 'ytimg.com',
        )):
            return 100
        if u.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')) or '.jpg?' in u or '.png?' in u:
            return 80
        if 'facebook.com/ads/image' in u:
            return 10
        if 'facebook.com' in u:
            return 20
        return 40

    return max(candidates, key=_score)


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
        'display_image_url': '',
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
        or creative.get('marketingImages')
        or creative.get('squareMarketingImages')
        or []
    )
    if isinstance(media_urls, str):
        media_urls = [media_urls]
    # Flatten nested {url: ...} objects from some Meta/Google payloads
    flat_urls = []
    for item in media_urls:
        if isinstance(item, dict):
            flat_urls.append(
                item.get('url')
                or item.get('src')
                or item.get('imageUrl')
                or item.get('fullSizeUrl')
                or (item.get('fullSize') or {}).get('url')
                or ''
            )
        else:
            flat_urls.append(str(item or ''))
    media_urls = [u for u in flat_urls if u]

    image_url = (
        creative.get('imageUrl')
        or creative.get('image_url')
        or creative.get('picture')
        or creative.get('image_hash_url')
        or creative.get('pinterestImageUrl')
        or creative.get('image')
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
        or creative.get('youtubeVideoId')
        or creative.get('youtube_video_id')
        or ''
    )
    video_url = (
        creative.get('videoUrl')
        or creative.get('video_url')
        or creative.get('video_src')
        or ''
    )
    if video_id and not video_url:
        # YouTube ids are typically 11 chars; Meta numeric → FB watch
        if len(video_id) == 11 and not video_id.isdigit():
            video_url = f'https://www.youtube.com/watch?v={video_id}'
        else:
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

    # RSA text fallbacks (arrays preferred)
    google_headlines = creative.get('googleHeadlines') or []
    google_descriptions = creative.get('googleDescriptions') or []

    def _first_text(rows, fallback=''):
        for row in rows or []:
            if isinstance(row, str) and row.strip():
                return row.strip()
            if isinstance(row, dict):
                text = (row.get('text') or row.get('value') or '').strip()
                if text:
                    return text
        return fallback

    title = (
        creative.get('title')
        or creative.get('name')
        or creative.get('googleHeadline')
        or _first_text(google_headlines)
        or ''
    )
    body = (
        creative.get('body')
        or creative.get('message')
        or creative.get('googleDescription')
        or _first_text(google_descriptions)
        or ''
    )

    if video_id or video_url or 'video' in object_type or 'reel' in object_type:
        media_type = 'video'
    elif image_url or thumbnail_url:
        media_type = 'image'
    elif permalink or ig_media_id or story_id:
        media_type = 'link'
    elif title or body:
        media_type = 'text'
    else:
        media_type = 'none'

    needs_refresh = media_type in ('none', 'link') and bool(ig_media_id or story_id or permalink)
    display_image_url = prefer_display_image_url(image_url, thumbnail_url)

    return {
        'media_type': media_type,
        'image_url': image_url or '',
        'thumbnail_url': thumbnail_url or '',
        'display_image_url': display_image_url or '',
        'video_url': video_url or '',
        'video_id': video_id,
        'body': body[:2000],
        'title': title[:500],
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
            ('google', 'Google Ads'),
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
    adset_id = fields.Many2one('tcrm.marketing.adset', string='Reklam Seti', ondelete='set null', index=True)
    adset_name = fields.Char(string='Reklam Seti Adı')
    creative_json = fields.Text(groups='tcrm_marketing_hub.group_marketing_admin')
    creative_media_type = fields.Char(string='Kreatif Tipi', compute='_compute_creative_preview', store=True)
    creative_image_url = fields.Char(string='Kreatif Görsel URL', compute='_compute_creative_preview', store=True)
    creative_video_url = fields.Char(string='Kreatif Video URL', compute='_compute_creative_preview', store=True)
    creative_thumbnail_url = fields.Char(string='Kreatif Önizleme URL', compute='_compute_creative_preview', store=True)
    creative_title = fields.Char(string='Kreatif Başlık', compute='_compute_creative_preview', store=True)
    creative_body = fields.Text(string='Kreatif Metin', compute='_compute_creative_preview', store=True)
    creative_permalink = fields.Char(string='Kreatif Bağlantı', compute='_compute_creative_preview', store=True)
    creative_html = fields.Html(string='Kreatif Önizleme', compute='_compute_creative_preview', store=True, sanitize=False)
    spend = fields.Float(string='Harcama')
    impressions = fields.Float(string='Gösterim')
    clicks = fields.Float(string='Tıklama')
    ctr = fields.Float(string='CTR (%)')
    cpc = fields.Float(string='CPC')
    cpm = fields.Float(string='CPM')
    meta_ads_manager_url = fields.Char(string='Meta Ads Manager Linki', compute='_compute_meta_ads_manager_url')
    last_sync_at = fields.Datetime(string='Son Senkron')

    _platform_ad_uniq = models.Constraint(
        'unique(platform_ad_id)',
        'Bu Meta reklam zaten kayıtlı.',
    )

    @api.depends('platform_ad_id', 'ad_account_id', 'ad_account_id.meta_act_id')
    def _compute_meta_ads_manager_url(self):
        for rec in self:
            act_id = rec.ad_account_id.meta_act_id if rec.ad_account_id else ''
            if act_id and rec.platform_ad_id:
                clean_act = act_id.replace('act_', '')
                rec.meta_ads_manager_url = f'https://adsmanager.facebook.com/adsmanager/manage/ads?act={clean_act}&selected_ad_ids={rec.platform_ad_id}'
            else:
                rec.meta_ads_manager_url = False

    @api.depends('creative_json', 'name')
    def _compute_creative_preview(self):
        for rec in self:
            preview = rec.get_creative_preview()
            rec.creative_media_type = preview.get('media_type') or 'none'
            rec.creative_image_url = preview.get('image_url') or False
            rec.creative_video_url = preview.get('video_url') or False
            rec.creative_thumbnail_url = preview.get('thumbnail_url') or preview.get('image_url') or False
            rec.creative_title = preview.get('title') or False
            rec.creative_body = preview.get('body') or False
            rec.creative_permalink = preview.get('permalink') or preview.get('link_url') or False

            from markupsafe import escape, Markup
            from urllib.parse import quote
            parts = []
            media_type = preview.get('media_type') or 'none'
            thumb = prefer_display_image_url(
                preview.get('image_url') or '',
                preview.get('thumbnail_url') or '',
            ) or preview.get('display_image_url') or ''
            v_url = preview.get('video_url') or ''
            v_id = preview.get('video_id') or ''
            p_url = preview.get('permalink') or preview.get('link_url') or ''
            b_text = preview.get('body') or ''
            t_text = preview.get('title') or ''

            if media_type == 'video':
                parts.append('<div style="margin-bottom:8px"><span style="background:#ede9fe;color:#6d28d9;padding:3px 10px;border-radius:4px;font-weight:600;font-size:11px"><i class="fa fa-video-camera me-1"></i>VİDEO / REEL KREATİF</span></div>')
                if v_url and ('facebook.com' in v_url or 'fb.watch' in v_url or v_id):
                    fb_video_href = v_url if 'facebook.com' in v_url else f'https://www.facebook.com/watch/?v={v_id}'
                    encoded_href = quote(fb_video_href)
                    parts.append(
                        f'<div style="max-width:500px;margin:0 auto"><iframe src="https://www.facebook.com/plugins/video.php?href={encoded_href}&amp;show_text=0" '
                        f'width="100%" height="280" style="border:none;overflow:hidden;border-radius:8px" scrolling="no" frameborder="0" allowfullscreen="true"></iframe></div>'
                    )
                elif v_url and v_url.endswith(('.mp4', '.mov', '.webm')):
                    parts.append(
                        f'<div style="max-width:500px;margin:0 auto"><video controls style="max-height:280px;width:100%;border-radius:8px" poster="{escape(thumb)}"><source src="{escape(v_url)}"/></video></div>'
                    )
                elif thumb:
                    parts.append(
                        f'<div style="max-width:480px;margin:0 auto"><a href="{escape(v_url or p_url or thumb)}" target="_blank" rel="noopener"><img src="{escape(thumb)}" referrerpolicy="no-referrer" style="max-height:260px;max-width:100%;border-radius:8px;object-fit:contain"/></a></div>'
                    )
                elif p_url and 'instagram.com' in p_url:
                    clean_p = p_url.split('?')[0].rstrip('/')
                    parts.append(
                        f'<div style="max-width:400px;margin:0 auto"><iframe src="{clean_p}/embed" width="100%" height="380" style="border:none;border-radius:8px" frameborder="0" scrolling="no"></iframe></div>'
                    )

            elif media_type == 'image' or thumb:
                parts.append('<div style="margin-bottom:8px"><span style="background:#cffafe;color:#0e7490;padding:3px 10px;border-radius:4px;font-weight:600;font-size:11px"><i class="fa fa-picture-o me-1"></i>GÖRSEL KREATİF</span></div>')
                if thumb:
                    parts.append(
                        f'<div style="max-width:480px;margin:0 auto"><a href="{escape(p_url or thumb)}" target="_blank" rel="noopener">'
                        f'<img src="{escape(thumb)}" referrerpolicy="no-referrer" crossorigin="anonymous" style="max-height:280px;max-width:100%;border-radius:8px;object-fit:contain"/>'
                        f'</a></div>'
                    )
                elif p_url and 'instagram.com' in p_url:
                    clean_p = p_url.split('?')[0].rstrip('/')
                    parts.append(
                        f'<div style="max-width:400px;margin:0 auto"><iframe src="{clean_p}/embed" width="100%" height="380" style="border:none;border-radius:8px" frameborder="0" scrolling="no"></iframe></div>'
                    )

            elif p_url:
                parts.append(
                    f'<div style="margin-bottom:8px"><span style="background:#fce7f3;color:#9d174d;padding:3px 10px;border-radius:4px;font-weight:600;font-size:11px"><i class="fa fa-link me-1"></i>META AD</span></div>'
                    f'<p><a class="btn btn-sm btn-outline-primary" href="{escape(p_url)}" target="_blank" rel="noopener">Kreatif Bağlantısını Aç &rarr;</a></p>'
                )
            else:
                parts.append('<p style="color:#94a3b8;font-size:12px">Görsel / Video kreatif önizleme bilgisi henüz yüklenmedi.</p>')

            if t_text:
                parts.append(f'<strong style="display:block;margin-top:8px;font-size:14px">{escape(t_text)}</strong>')
            if b_text:
                parts.append(f'<p style="margin-top:4px;font-size:12px;color:#475569;white-space:pre-wrap">{escape(b_text[:400])}</p>')
            rec.creative_html = Markup(''.join(parts))

    def get_creative_preview(self):
        self.ensure_one()
        return extract_creative_preview(self.creative_json)

    def write(self, vals):
        res = super().write(vals)
        if any(k == 'creative_json' or k.startswith('creative_') for k in vals):
            MetaLead = self.env['tcrm.marketing.meta.lead'].sudo()
            ad_ids = [str(a) for a in self.mapped('platform_ad_id') if a]
            if ad_ids:
                leads = MetaLead.search([('ad_id', 'in', ad_ids)])
                if leads:
                    leads.with_context(marketing_skip_creative=True).action_refresh_creative_preview()
        return res

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
            if preview.get('media_type') in ('image', 'video', 'link', 'text'):
                refreshed += 1
        return refreshed

    @api.model
    def action_refresh_all_creatives(self, *, limit=200, only_thin=True):
        """Backfill creative media for ads missing image/video URLs.

        Paces Zernio calls to reduce rate-limit thrashing.
        """
        import time
        domain = [('company_id', '=', self.env.company.id)]
        if only_thin:
            domain += [
                '|', '|',
                ('creative_media_type', 'in', ('none', 'link', False)),
                ('creative_thumbnail_url', '=', False),
                ('creative_image_url', '=', False),
            ]
        ads = self.search(domain, limit=limit, order='write_date desc')
        refreshed = 0
        for ad in ads:
            try:
                n = ad.action_refresh_creative_from_zernio()
                if n:
                    refreshed += 1
            except Exception as exc:
                _logger.debug('Creative refresh failed for %s: %s', ad.platform_ad_id, exc)
            time.sleep(0.35)
        return refreshed


class MarketingCampaign(models.Model):
    _name = 'tcrm.marketing.campaign'
    _description = 'Reklam Kampanyası'
    _order = 'write_date desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Kampanya Adı', required=True, tracking=True)
    zernio_id = fields.Char(string='Kampanya ID', index=True, copy=False)
    platform_campaign_id = fields.Char(string='Platform Kampanya ID', index=True)
    platform = fields.Selection(
        [
            ('facebook', 'Facebook'),
            ('instagram', 'Instagram'),
            ('meta', 'Meta (Facebook + Instagram)'),
            ('google', 'Google Ads'),
        ],
        string='Platform',
        default='meta',
        tracking=True,
    )
    channel_type = fields.Char(
        string='Kanal Tipi',
        help='Google: SEARCH / DISPLAY / PERFORMANCE_MAX / …',
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
    adset_ids = fields.One2many('tcrm.marketing.adset', 'campaign_id', string='Reklam Setleri')
    adset_count = fields.Integer(string='Reklam Seti Sayısı', compute='_compute_counts')
    ad_count = fields.Integer(string='Reklam Sayısı', compute='_compute_counts')

    @api.depends('adset_ids', 'meta_ad_ids')
    def _compute_counts(self):
        for rec in self:
            rec.adset_count = len(rec.adset_ids)
            rec.ad_count = len(rec.meta_ad_ids)

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
        """Best-effort: connect/scope Meta Ads for each Facebook page.

        Returns list of human-readable errors (e.g. Zernio plan / payment limits).
        """
        errors = []
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
                # Unique act ids — FB+IG duplicates share the same Meta act
                act_ids = list(dict.fromkeys(acts.mapped('meta_act_id')))
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
                        errors.append(str(exc2))
        return errors

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
        item_plat = (item.get('platform') or '').lower().strip()
        is_google = item_plat in ('google', 'googleads')
        if is_google:
            platform = 'google'
        else:
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
            'channel_type': (
                item.get('advertisingChannelType')
                or item.get('channelType')
                or False
            ),
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
        MetaAdSet = self.env['tcrm.marketing.adset'].sudo()
        ads_out = []

        for aset in item.get('adSets') or item.get('adsets') or []:
            aset_name = aset.get('adSetName') or aset.get('name') or ''
            padset_id = str(aset.get('platformAdSetId') or aset.get('id') or aset.get('_id') or '')
            adset_rec = MetaAdSet.browse()
            if padset_id:
                aset_metrics = aset.get('metrics') or {}
                aset_budget = aset.get('budget') or {}
                aset_vals = {
                    'name': aset_name or f'Reklam Seti {padset_id}',
                    'platform_adset_id': padset_id,
                    'zernio_id': str(aset.get('_id') or '') or False,
                    'status': aset.get('status') or 'ACTIVE',
                    'daily_budget': float(aset_budget.get('amount') or aset.get('dailyBudget') or 0),
                    'campaign_id': campaign.id,
                    'ad_account_id': ad_account.id if ad_account else False,
                    'account_id': social_account.id if social_account else False,
                    'company_id': campaign.company_id.id,
                    'spend': float(aset_metrics.get('spend') or 0),
                    'impressions': float(aset_metrics.get('impressions') or 0),
                    'clicks': float(aset_metrics.get('clicks') or aset_metrics.get('linkClicks') or 0),
                    'last_sync_at': fields.Datetime.now(),
                    'raw_json': json.dumps(aset, ensure_ascii=False, default=str)[:8000],
                }
                found_aset = MetaAdSet.search([('platform_adset_id', '=', padset_id)], limit=1)
                if found_aset:
                    found_aset.write(aset_vals)
                    adset_rec = found_aset
                else:
                    adset_rec = MetaAdSet.create(aset_vals)

            for ad in aset.get('ads') or []:
                pad = ad.get('platformAdId') or ad.get('id') or ad.get('_id')
                if not pad:
                    continue
                creative = ad.get('creative') or {}
                ad_name = ad.get('name') or ad.get('adName') or f'Reklam {pad}'
                if is_google or (ad.get('platform') or '').lower() in ('google', 'googleads'):
                    src = 'google'
                else:
                    src = detect_placement_platform(
                        name=f'{ad_name} {aset_name}',
                        campaign_name=camp_name,
                        creative=creative,
                    )
                ad_metrics = ad.get('metrics') or {}
                ad_vals = {
                    'name': ad_name,
                    'platform_ad_id': str(pad),
                    'zernio_id': str(ad.get('_id') or '') or False,
                    'source_platform': src,
                    'status': ad.get('status') or False,
                    'campaign_id': campaign.id,
                    'adset_id': adset_rec.id if adset_rec else False,
                    'adset_name': adset_rec.name if adset_rec else (aset_name or False),
                    'ad_account_id': ad_account.id if ad_account else False,
                    'account_id': social_account.id if social_account else False,
                    'company_id': campaign.company_id.id,
                    'creative_json': json.dumps(creative, ensure_ascii=False, default=str)[:8000],
                    'spend': float(ad_metrics.get('spend') or 0),
                    'impressions': float(ad_metrics.get('impressions') or 0),
                    'clicks': float(ad_metrics.get('clicks') or ad_metrics.get('linkClicks') or 0),
                    'ctr': float(ad_metrics.get('ctr') or 0),
                    'cpc': float(ad_metrics.get('cpc') or 0),
                    'cpm': float(ad_metrics.get('cpm') or 0),
                    'last_sync_at': fields.Datetime.now(),
                }
                found = MetaAd.search([('platform_ad_id', '=', str(pad))], limit=1)
                if found:
                    found.write(ad_vals)
                    ad_rec = found
                else:
                    ad_rec = MetaAd.create(ad_vals)

                # Refresh thin creatives for Meta + Google (tree often lacks media URLs)
                if not self.env.context.get('marketing_skip_creative'):
                    prev = ad_rec.get_creative_preview()
                    if prev.get('media_type') in ('none', 'link', 'text') and prev.get('needs_refresh', True):
                        # Always try Meta; Google only when no RSA text yet or PMax empty media
                        if src != 'google' or prev.get('media_type') in ('none', 'link'):
                            try:
                                ad_rec.action_refresh_creative_from_zernio()
                            except Exception:
                                pass
                ads_out.append(ad_rec)
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

        connect_errors = self._ensure_meta_ads_connected(client)

        ad_accounts = self.env['tcrm.marketing.ad.account'].search([('active', '=', True)])
        if not ad_accounts:
            raise UserError(_(
                'Önce Meta reklam hesabı bağlayın / senkronize edin '
                '(Marketing Hub → Reklam Hesapları).'
            ))

        # One sync pass per platform act id — prefer dedicated ads connections
        seen_acts = set()
        unique_accounts = self.env['tcrm.marketing.ad.account']
        platform_rank = {
            'metaads': 0,
            'googleads': 0,
            'facebook': 1,
            'instagram': 2,
        }
        ordered = ad_accounts.sorted(
            key=lambda a: (
                platform_rank.get(a.account_id.platform, 9),
                0 if a.provider == 'google' else 1,
                a.id,
            )
        )
        for ad_acc in ordered:
            act = ad_acc.meta_act_id or ''
            # Dedupe Meta acts across facebook/instagram/metaads rows
            dedupe_key = f'{ad_acc.provider}:{act}'
            if not act or dedupe_key in seen_acts:
                continue
            seen_acts.add(dedupe_key)
            unique_accounts |= ad_acc

        synced = 0
        errors = list(connect_errors)
        for ad_acc in unique_accounts:
            page = 1
            while page <= 40:
                try:
                    tree = client.get_ads_tree(
                        page=page,
                        limit=50,
                        source='all',
                        ad_account_id=ad_acc.meta_act_id,
                        account_id=ad_acc.account_id.zernio_id if ad_acc.account_id else None,
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

        # Also sync Google keywords after campaign tree
        try:
            self.env['tcrm.marketing.google.keyword'].action_sync_from_zernio()
        except Exception as exc:
            _logger.warning('Google keyword sync after campaigns failed: %s', exc)
            errors.append(f'keywords: {exc}')

        if not synced and connect_errors:
            # Surface Zernio plan limits clearly (e.g. free tier: max 2 accounts)
            raise UserError(_(
                'Kampanyalar çekilemedi. Zernio Meta Ads bağlantısı başarısız:\n\n%s\n\n'
                'Zernio ücretsiz planda en fazla 2 hesap bağlanabilir (Facebook + Instagram '
                'doluysa Meta Ads için ödeme yöntemi / plan yükseltme gerekir).'
            ) % '\n'.join(connect_errors[:3]))

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
