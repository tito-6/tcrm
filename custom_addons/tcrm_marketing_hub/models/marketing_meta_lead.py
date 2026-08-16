# -*- coding: utf-8 -*-
import json
import logging
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote

from markupsafe import Markup, escape
from tcrm import _, api, fields, models
from tcrm.exceptions import UserError

from ..services.zernio_client import ZernioError
from .marketing_ad import detect_placement_platform, extract_creative_preview, prefer_display_image_url

_logger = logging.getLogger(__name__)

SOURCE_LABELS = {
    'instagram': 'Instagram',
    'facebook': 'Facebook',
    'meta': 'Meta',
}


# Meta Lead Forms often use locale-specific keys (TR: adı_soyadı, telefon_numarası, e-posta).
_NAME_KEYS = (
    'full_name', 'fullname', 'name', 'adı_soyadı', 'adi_soyadi', 'ad_soyad',
    'adınız_soyadınız', 'adiniz_soyadiniz', 'first_name', 'last_name',
)
_EMAIL_KEYS = (
    'email', 'e-posta', 'e_posta', 'eposta', 'email_address', 'work_email',
)
_PHONE_KEYS = (
    'phone_number', 'phone', 'telefon_numarası', 'telefon_numarasi', 'telefon',
    'mobile', 'mobile_number', 'cep_telefonu', 'gsm',
)
_COMPANY_KEYS = (
    'şirket_adı', 'sirket_adi', 'company_name', 'company', 'işletme_adı', 'isletme_adi',
)


def _norm_field_key(key):
    """Normalize Meta form field names for fuzzy matching."""
    text = str(key or '').strip().lower()
    # Common Turkish diacritics → ascii for matching
    trans = str.maketrans({
        'ı': 'i', 'İ': 'i', 'ş': 's', 'Ş': 's', 'ğ': 'g', 'Ğ': 'g',
        'ü': 'u', 'Ü': 'u', 'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c',
    })
    text = text.translate(trans)
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')


def _fields_map_get(fields_map, candidates):
    """Pick first non-empty value matching any candidate key (exact or normalized)."""
    if not fields_map:
        return False
    # Exact keys first
    for key in candidates:
        val = fields_map.get(key)
        if val not in (None, False, ''):
            return str(val).strip() or False
        # Case-insensitive exact
        for raw_key, raw_val in fields_map.items():
            if str(raw_key).lower() == key.lower() and raw_val not in (None, False, ''):
                return str(raw_val).strip() or False
    # Normalized fuzzy
    wanted = {_norm_field_key(c) for c in candidates}
    for raw_key, raw_val in fields_map.items():
        if raw_val in (None, False, ''):
            continue
        if _norm_field_key(raw_key) in wanted:
            return str(raw_val).strip() or False
    return False


def _extract_contact_from_fields(fields_map):
    """Extract contact_name / email / phone / company from Meta lead field map."""
    fields_map = fields_map or {}
    first = _fields_map_get(fields_map, ('first_name', 'ad', 'adı', 'adi'))
    last = _fields_map_get(fields_map, ('last_name', 'soyad', 'soyadı', 'soyadi'))
    name = _fields_map_get(fields_map, _NAME_KEYS)
    if not name and (first or last):
        name = ' '.join(p for p in (first, last) if p).strip() or False
    return {
        'contact_name': name,
        'email': _fields_map_get(fields_map, _EMAIL_KEYS),
        'phone': _fields_map_get(fields_map, _PHONE_KEYS),
        'company_name': _fields_map_get(fields_map, _COMPANY_KEYS),
    }


def _parse_meta_dt(value):
    """Parse Meta/Zernio timestamps like 2026-07-24T12:00:17+0000."""
    if not value:
        return False
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    text = str(value).strip()
    for fmt in (
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
    ):
        try:
            dt = datetime.strptime(text.replace('Z', '+0000'), fmt)
            return dt.replace(tzinfo=None)
        except ValueError:
            continue
    try:
        return fields.Datetime.to_datetime(text.replace('T', ' ')[:19])
    except Exception:
        return False


class MarketingLeadForm(models.Model):
    _name = 'tcrm.marketing.lead.form'
    _description = 'Meta Lead Gen Formu'
    _order = 'leads_count desc, name'

    name = fields.Char(string='Form Adı', required=True)
    zernio_form_id = fields.Char(string='Meta Form ID', required=True, index=True)
    status = fields.Char(string='Durum')
    locale = fields.Char(string='Dil')
    leads_count = fields.Integer(string='Meta Lead Sayısı')
    account_id = fields.Many2one(
        'tcrm.marketing.account',
        string='Sayfa / Hesap',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(related='account_id.company_id', store=True, readonly=True)
    lead_ids = fields.One2many('tcrm.marketing.meta.lead', 'form_id', string='Leadler')
    imported_lead_count = fields.Integer(compute='_compute_imported_count')
    last_sync_at = fields.Datetime(string='Son Senkron')
    questions_json = fields.Text(groups='tcrm_marketing_hub.group_marketing_admin')

    _sql_constraints = [
        ('form_account_uniq', 'unique(zernio_form_id, account_id)', 'Bu form zaten kayıtlı.'),
    ]

    @api.depends('lead_ids', 'lead_ids.crm_lead_id')
    def _compute_imported_count(self):
        for rec in self:
            rec.imported_lead_count = len(rec.lead_ids.filtered('crm_lead_id'))

    @api.model
    def _metaads_account_for_company(self):
        """Connected Meta Ads Zernio account for this company (preferred lead-gen credential)."""
        return self.env['tcrm.marketing.account'].sudo().search([
            ('platform', '=', 'metaads'),
            ('active', '=', True),
            ('sync_enabled', '=', True),
            ('company_id', '=', self.env.company.id),
            ('status', '!=', 'disconnected'),
        ], limit=1)

    @api.model
    def action_sync_from_zernio(self):
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        metaads = self._metaads_account_for_company()
        # Prefer Meta Ads credential first — Facebook page social may be disconnected
        # while Meta Ads remains connected and can still pull /ads/lead-forms/{id}/leads.
        accounts = self.env['tcrm.marketing.account'].search([
            ('platform', 'in', ('metaads', 'facebook')),
            ('active', '=', True),
            ('sync_enabled', '=', True),
            ('company_id', '=', self.env.company.id),
        ], order='platform desc, id asc')  # metaads before facebook
        synced = 0
        for social in accounts:
            try:
                data = client.list_lead_forms(account_id=social.zernio_id, limit=50)
            except ZernioError as exc:
                _logger.warning('Lead forms sync failed for %s: %s', social.zernio_id, exc)
                err = str(exc)
                err_l = err.lower()
                for secret_key in ('api_key', 'apiKey', 'token', 'Bearer', 'authorization'):
                    if secret_key.lower() in err_l:
                        err = _('Senkron hatası (ayrıntılar gizlendi).')
                        break
                # Meta Ads often cannot list forms (403) but can still pull
                # /ads/lead-forms/{id}/leads for known forms. Do not mark it
                # disconnected or overwrite a healthy credential status.
                if social.platform == 'metaads' and getattr(exc, 'status_code', None) in (401, 403):
                    _logger.info(
                        'Skipping lead-forms list for Meta Ads %s; known forms still sync via lead pull',
                        social.zernio_id,
                    )
                    continue
                write_vals = {'sync_error': err[:2000]}
                if 'not found' in err_l or 'social account' in err_l:
                    write_vals['status'] = 'disconnected'
                social.sudo().write(write_vals)
                continue
            social.sudo().write({
                'sync_error': False,
                'status': 'connected',
                'last_sync_at': fields.Datetime.now(),
            })
            for item in data.get('forms') or []:
                fid = item.get('id') or item.get('_id')
                if not fid:
                    continue
                vals = {
                    'name': item.get('name') or fid,
                    'zernio_form_id': str(fid),
                    'status': item.get('status') or False,
                    'locale': item.get('locale') or False,
                    'leads_count': int(item.get('leads_count') or item.get('leadsCount') or 0),
                    'account_id': social.id,
                    'last_sync_at': fields.Datetime.now(),
                    'questions_json': json.dumps(
                        item.get('questions') or [], ensure_ascii=False, default=str
                    )[:12000],
                }
                existing = self.sudo().search([
                    ('zernio_form_id', '=', str(fid)),
                    ('account_id', '=', social.id),
                ], limit=1)
                if existing:
                    existing.write(vals)
                else:
                    stale = self.sudo().search([
                        ('zernio_form_id', '=', str(fid)),
                        ('company_id', '=', self.env.company.id),
                    ], limit=1)
                    if stale:
                        stale.write(vals)
                    else:
                        self.sudo().create(vals)
                synced += 1

        # If list_lead_forms is unavailable on Meta Ads but forms already exist
        # (legacy Facebook social), remap them onto the connected Meta Ads account
        # so lead pulls use a working credential.
        if metaads:
            stale_forms = self.sudo().search([
                ('company_id', '=', self.env.company.id),
                ('account_id.platform', '!=', 'metaads'),
            ])
            for form in stale_forms:
                form.write({'account_id': metaads.id})
                synced += 1
                _logger.info(
                    'Remapped lead form %s onto Meta Ads account %s',
                    form.zernio_form_id,
                    metaads.zernio_id,
                )
        return synced

    def _lead_pull_account(self):
        """Zernio account id to use for form lead pulls (prefer Meta Ads)."""
        self.ensure_one()
        metaads = self._metaads_account_for_company()
        if metaads:
            if self.account_id.id != metaads.id:
                self.sudo().write({'account_id': metaads.id})
            return metaads
        return self.account_id

    @api.model
    def _discover_lead_ad_sources(self):
        """Discover native-lead ad IDs when Meta Ads cannot list Page forms.

        Zernio's Meta Ads credential can pull leads through
        /ads/lead-forms/{ad_id}/leads even when /ads/lead-forms returns 403.
        One ads-tree request per ad account keeps discovery rate-limit friendly.
        """
        metaads = self._metaads_account_for_company()
        if not metaads:
            return 0
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
        except ZernioError:
            return 0

        AdAccount = self.env['tcrm.marketing.ad.account'].sudo()
        ad_accounts = AdAccount.search([
            ('account_id', '=', metaads.id),
            ('active', '=', True),
            ('provider', '!=', 'google'),
        ])
        date_to = fields.Date.today()
        date_from = date_to - timedelta(days=30)
        created_cutoff = datetime.combine(date_from, datetime.min.time())
        discovered = 0
        discovered_ids = set()
        successful_accounts = 0
        for ad_account in ad_accounts:
            try:
                data = client.get_ads_tree(
                    page=1,
                    limit=50,
                    source='all',
                    account_id=metaads.zernio_id,
                    ad_account_id=ad_account.meta_act_id,
                    date_from=date_from.isoformat(),
                    date_to=date_to.isoformat(),
                )
            except ZernioError as exc:
                _logger.warning(
                    'Lead ad discovery failed account=%s: %s',
                    ad_account.meta_act_id,
                    exc,
                )
                continue
            successful_accounts += 1
            for campaign in data.get('campaigns') or []:
                objective = str(campaign.get('platformObjective') or '').upper()
                if 'LEAD' not in objective:
                    continue
                for adset in campaign.get('adSets') or []:
                    for ad in adset.get('ads') or []:
                        ad_id = str(ad.get('platformAdId') or '').strip()
                        if not ad_id:
                            continue
                        created_at = _parse_meta_dt(ad.get('platformCreatedAt'))
                        if created_at and created_at < created_cutoff:
                            continue
                        discovered_ids.add(ad_id)
                        vals = {
                            'name': ad.get('adName') or f'Perla Meta Lead Ad {ad_id}',
                            'zernio_form_id': ad_id,
                            'status': 'AD_SOURCE_ACTIVE',
                            'account_id': metaads.id,
                            'last_sync_at': fields.Datetime.now(),
                        }
                        form = self.sudo().search([
                            ('zernio_form_id', '=', ad_id),
                            ('company_id', '=', self.env.company.id),
                        ], limit=1)
                        if form:
                            form.write(vals)
                        else:
                            self.sudo().create(vals)
                        discovered += 1
        if successful_accounts:
            stale = self.sudo().search([
                ('company_id', '=', self.env.company.id),
                ('account_id', '=', metaads.id),
                ('status', '=', 'AD_SOURCE_ACTIVE'),
                ('zernio_form_id', 'not in', list(discovered_ids) or ['0']),
            ])
            if stale:
                stale.write({'status': 'AD_SOURCE_INACTIVE'})
        return discovered

    def action_sync_leads_button(self):
        for form in self:
            form.action_sync_leads(limit_pages=20, import_crm=True)
        return True

    def action_sync_leads(self, *, limit_pages: int = 10, import_crm: bool = True):
        """Pull leads for this form and optionally create crm.lead records."""
        self.ensure_one()
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        pull_account = self._lead_pull_account()
        if not pull_account or not pull_account.zernio_id:
            raise UserError(_('Lead çekmek için bağlı bir Meta Ads hesabı bulunamadı.'))

        MetaLead = self.env['tcrm.marketing.meta.lead'].sudo()
        cursor = None
        created = 0
        bulk = MetaLead.with_context(marketing_skip_creative=True)
        try:
            for _ in range(limit_pages):
                data = client.list_form_leads(
                    self.zernio_form_id,
                    account_id=pull_account.zernio_id,
                    limit=50,
                    cursor=cursor,
                )
                rows = data.get('leads') or []
                for item in rows:
                    lead = bulk._upsert_from_remote(item, form=self)
                    if lead:
                        created += 1
                        if import_crm and not lead.crm_lead_id:
                            lead.with_context(marketing_skip_creative=True).action_import_to_crm()
                        elif import_crm and lead.crm_lead_id:
                            lead._sync_crm_source()
                pagination = data.get('pagination') or {}
                cursor = pagination.get('cursor')
                if not pagination.get('hasMore') or not cursor:
                    break
                # Gentle pacing between pages to reduce Zernio rate limits
                time.sleep(1.5)
        except ZernioError as exc:
            err = str(exc)
            _logger.warning(
                'Lead pull failed form=%s account=%s: %s',
                self.zernio_form_id,
                pull_account.zernio_id,
                exc,
            )
            write_vals = {'sync_error': err[:2000]}
            if 'not found' in err.lower() or 'social account' in err.lower():
                write_vals['status'] = 'disconnected'
            pull_account.sudo().write(write_vals)
            raise
        self.last_sync_at = fields.Datetime.now()
        if pull_account.sync_error:
            pull_account.sudo().write({
                'sync_error': False,
                'status': 'connected',
                'last_sync_at': fields.Datetime.now(),
            })
        return created


class MarketingMetaLead(models.Model):
    _name = 'tcrm.marketing.meta.lead'
    _description = 'Meta Lead Gen Kaydı'
    _order = 'created_time desc, id desc'
    _rec_name = 'contact_name'

    contact_name = fields.Char(string='Ad Soyad')
    email = fields.Char(string='E-posta')
    phone = fields.Char(string='Telefon')
    company_name = fields.Char(string='Şirket Adı')
    leadgen_id = fields.Char(string='Meta Lead ID', required=True, index=True, copy=False)
    form_id = fields.Many2one(
        'tcrm.marketing.lead.form',
        string='Form',
        required=True,
        ondelete='cascade',
        index=True,
    )
    account_id = fields.Many2one(related='form_id.account_id', store=True, readonly=True)
    company_id = fields.Many2one(related='form_id.company_id', store=True, readonly=True)
    ad_id = fields.Char(string='Meta Ad ID', index=True)
    ad_name = fields.Char(string='Reklam Adı')
    campaign_id_remote = fields.Char(string='Meta Kampanya ID')
    campaign_name = fields.Char(string='Kampanya Adı')
    source_platform = fields.Selection(
        [
            ('facebook', 'Facebook'),
            ('instagram', 'Instagram'),
            ('meta', 'Meta'),
        ],
        string='Kaynak',
        default='meta',
        index=True,
        help='Leadin geldiği yayın yüzeyi (Instagram / Facebook / Meta).',
    )
    created_time = fields.Datetime(string='Gönderim Zamanı (Meta)')
    fields_json = fields.Text(string='Alanlar (JSON)')
    summary = fields.Text(string='Özet', compute='_compute_summary', store=True)
    crm_lead_id = fields.Many2one('crm.lead', string='TCRM Lead', copy=False, index=True)
    state = fields.Selection(
        [('new', 'Yeni'), ('imported', 'CRM’e Aktarıldı'), ('skipped', 'Atlandı')],
        string='Durum',
        default='new',
    )
    creative_media_type = fields.Char(
        string='Kreatif Tipi',
        compute='_compute_creative_preview',
        store=True,
    )
    creative_image_url = fields.Char(
        string='Kreatif Görsel URL',
        compute='_compute_creative_preview',
        store=True,
    )
    creative_video_url = fields.Char(
        string='Kreatif Video URL',
        compute='_compute_creative_preview',
        store=True,
    )
    creative_thumbnail_url = fields.Char(
        string='Kreatif Önizleme URL',
        compute='_compute_creative_preview',
        store=True,
    )
    creative_body = fields.Text(
        string='Kreatif Metin',
        compute='_compute_creative_preview',
        store=True,
    )
    creative_permalink = fields.Char(
        string='Kreatif Bağlantı',
        compute='_compute_creative_preview',
        store=True,
    )
    creative_html = fields.Html(
        string='Kreatif Önizleme HTML',
        compute='_compute_creative_preview',
        store=True,
        sanitize=False,
    )

    _sql_constraints = [
        ('leadgen_uniq', 'unique(leadgen_id)', 'Bu Meta lead zaten kayıtlı.'),
    ]

    @api.model
    def _strip_platform_prefix(self, name):
        """Remove leading [Instagram] / [Facebook] / [Meta] from lead titles."""
        text = (name or '').strip()
        return re.sub(
            r'^\s*\[(?:Instagram|Facebook|Meta|IG|FB)\]\s*',
            '',
            text,
            flags=re.IGNORECASE,
        ).strip() or text

    def _ensure_ad_creative_cached(self, ad_id):
        """Load/refresh Meta ad creative via Zernio get_ad(platformAdId).

        Meta leadgen often returns ad IDs that are not in /ads (paused/deleted).
        Fallback: most recent cached ad with media for the same page/account.
        """
        MetaAd = self.env['tcrm.marketing.meta.ad'].sudo()
        cached = MetaAd.browse()
        if ad_id:
            cached = MetaAd.search([('platform_ad_id', '=', str(ad_id))], limit=1)
            preview = cached.get_creative_preview() if cached else extract_creative_preview({})
            if cached and preview.get('media_type') in ('image', 'video'):
                return cached
            try:
                client = self.env['tcrm.marketing.profile']._get_zernio_client()
                remote = client.get_ad(str(ad_id)) or {}
            except Exception as exc:
                _logger.warning('Creative fetch for ad %s failed: %s', ad_id, exc)
                remote = {}
            creative = remote.get('creative') or {}
            if creative:
                vals = {
                    'name': remote.get('name') or (cached.name if cached else False) or str(ad_id),
                    'platform_ad_id': str(remote.get('platformAdId') or ad_id),
                    'zernio_id': str(remote.get('_id') or (cached.zernio_id if cached else '') or '') or False,
                    'source_platform': (
                        'instagram' if (remote.get('platform') or '').lower() == 'instagram'
                        else 'facebook' if (remote.get('platform') or '').lower() == 'facebook'
                        else (cached.source_platform if cached else 'meta')
                    ),
                    'company_id': self.env.company.id,
                    'creative_json': json.dumps(creative, ensure_ascii=False, default=str)[:8000],
                    'last_sync_at': fields.Datetime.now(),
                }
                if cached:
                    cached.write(vals)
                    return cached
                return MetaAd.create(vals)
        # Fallback: recent ad with real media for this lead's page/company
        domain = [('company_id', '=', self.env.company.id)]
        account = False
        if self and self.form_id and self.form_id.account_id:
            account = self.form_id.account_id
            domain.append(('account_id', '=', account.id))
        candidates = MetaAd.search(domain, order='last_sync_at desc, id desc', limit=40)
        for ad in candidates:
            prev = ad.get_creative_preview()
            if prev.get('media_type') in ('image', 'video'):
                return ad
        return cached or MetaAd.browse()

    def action_refresh_creative_preview(self):
        """Recompute creative fields from cached Meta ads (optionally fetch missing)."""
        skip_fetch = self.env.context.get('marketing_skip_creative')
        for rec in self:
            if rec.ad_id and not skip_fetch:
                rec._ensure_ad_creative_cached(rec.ad_id)
        self.invalidate_recordset([
            'creative_media_type', 'creative_image_url', 'creative_video_url',
            'creative_thumbnail_url', 'creative_body', 'creative_permalink', 'creative_html',
        ])
        self._compute_creative_preview()
        return True

    @api.depends('ad_id', 'ad_name', 'campaign_name', 'campaign_id_remote', 'form_id')
    def _compute_creative_preview(self):
        MetaAd = self.env['tcrm.marketing.meta.ad'].sudo()
        Campaign = self.env['tcrm.marketing.campaign'].sudo()
        for rec in self:
            preview = extract_creative_preview({})
            cached = MetaAd.browse()
            if rec.ad_id:
                cached = MetaAd.search([('platform_ad_id', '=', str(rec.ad_id))], limit=1)
                if cached:
                    preview = cached.get_creative_preview()
            if (not cached or preview.get('media_type') in ('none', 'link')) and rec.ad_name:
                by_name = MetaAd.search([('name', '=ilike', rec.ad_name)], limit=1)
                if by_name:
                    cached = by_name
                    preview = cached.get_creative_preview()
            if (not cached or preview.get('media_type') in ('none', 'link')) and rec.campaign_name:
                camp = Campaign.search([('name', '=ilike', rec.campaign_name)], limit=1)
                if camp and camp.meta_ad_ids:
                    for ad in camp.meta_ad_ids:
                        prev = ad.get_creative_preview()
                        if prev.get('media_type') in ('image', 'video'):
                            cached = ad
                            preview = prev
                            break
            # Last resort (read-only): recent cached creative with media for same page
            if not cached or preview.get('media_type') in ('none', 'link'):
                domain = [('company_id', '=', rec.company_id.id or rec.env.company.id)]
                if rec.form_id and rec.form_id.account_id:
                    domain.append(('account_id', '=', rec.form_id.account_id.id))
                for ad in MetaAd.search(domain, order='last_sync_at desc, id desc', limit=40):
                    prev = ad.get_creative_preview()
                    if prev.get('media_type') in ('image', 'video'):
                        cached = ad
                        preview = prev
                        break

            media_type = preview.get('media_type') or 'none'
            image_url = preview.get('image_url') or ''
            thumb_raw = preview.get('thumbnail_url') or ''
            thumb = prefer_display_image_url(image_url, thumb_raw) or preview.get('display_image_url') or ''
            video_url = preview.get('video_url') or ''
            permalink = preview.get('permalink') or preview.get('link_url') or ''
            body = preview.get('body') or ''
            rec.creative_media_type = media_type
            rec.creative_image_url = image_url or False
            rec.creative_video_url = video_url or False
            rec.creative_thumbnail_url = thumb or thumb_raw or False
            rec.creative_body = body or False
            rec.creative_permalink = permalink or False
            parts = []
            v_id = preview.get('video_id') or ''

            if media_type == 'video':
                parts.append('<div style="margin-bottom:8px"><span style="background:#ede9fe;color:#6d28d9;padding:3px 10px;border-radius:4px;font-weight:600;font-size:11px"><i class="fa fa-video-camera me-1"></i>VİDEO / REEL KREATİF</span></div>')
                if video_url and ('facebook.com' in video_url or 'fb.watch' in video_url or v_id):
                    fb_video_href = video_url if 'facebook.com' in video_url else f'https://www.facebook.com/watch/?v={v_id}'
                    encoded_href = quote(fb_video_href)
                    parts.append(
                        f'<div style="max-width:500px;margin:0 auto"><iframe src="https://www.facebook.com/plugins/video.php?href={encoded_href}&amp;show_text=0" '
                        f'width="100%" height="280" style="border:none;overflow:hidden;border-radius:8px" scrolling="no" frameborder="0" allowfullscreen="true"></iframe></div>'
                    )
                elif video_url and video_url.endswith(('.mp4', '.mov', '.webm')):
                    parts.append(
                        f'<div style="max-width:500px;margin:0 auto"><video controls style="max-height:280px;width:100%;border-radius:8px" poster="{escape(thumb)}"><source src="{escape(video_url)}"/></video></div>'
                    )
                elif thumb:
                    parts.append(
                        f'<div style="max-width:480px;margin:0 auto"><a href="{escape(video_url or permalink or thumb)}" target="_blank" rel="noopener"><img src="{escape(thumb)}" referrerpolicy="no-referrer" style="max-height:260px;max-width:100%;border-radius:8px;object-fit:contain"/></a></div>'
                    )
                elif permalink and 'instagram.com' in permalink:
                    clean_p = permalink.split('?')[0].rstrip('/')
                    parts.append(
                        f'<div style="max-width:400px;margin:0 auto"><iframe src="{clean_p}/embed" width="100%" height="380" style="border:none;border-radius:8px" frameborder="0" scrolling="no"></iframe></div>'
                    )

            elif media_type == 'image' or thumb:
                parts.append('<div style="margin-bottom:8px"><span style="background:#cffafe;color:#0e7490;padding:3px 10px;border-radius:4px;font-weight:600;font-size:11px"><i class="fa fa-picture-o me-1"></i>GÖRSEL KREATİF</span></div>')
                if thumb:
                    parts.append(
                        f'<div style="max-width:480px;margin:0 auto"><a href="{escape(permalink or thumb)}" target="_blank" rel="noopener">'
                        f'<img src="{escape(thumb)}" referrerpolicy="no-referrer" crossorigin="anonymous" style="max-height:280px;max-width:100%;border-radius:8px;object-fit:contain"/>'
                        f'</a></div>'
                    )
                elif permalink and 'instagram.com' in permalink:
                    clean_p = permalink.split('?')[0].rstrip('/')
                    parts.append(
                        f'<div style="max-width:400px;margin:0 auto"><iframe src="{clean_p}/embed" width="100%" height="380" style="border:none;border-radius:8px" frameborder="0" scrolling="no"></iframe></div>'
                    )

            elif permalink:
                parts.append(
                    f'<div style="margin-bottom:8px"><span style="background:#fce7f3;color:#9d174d;padding:3px 10px;border-radius:4px;font-weight:600;font-size:11px"><i class="fa fa-link me-1"></i>META AD</span></div>'
                    f'<p><a class="btn btn-sm btn-outline-primary" href="{escape(permalink)}" target="_blank" rel="noopener">Kreatif Bağlantısını Aç &rarr;</a></p>'
                )
            else:
                parts.append('<p style="color:#94a3b8;font-size:12px">Görsel / Video kreatif önizleme bilgisi henüz yüklenmedi.</p>')

            if body:
                parts.append(
                    f'<p style="margin-top:10px;white-space:pre-wrap">{escape(body)}</p>'
                )
            rec.creative_html = Markup(''.join(parts))

    @api.depends('fields_json', 'contact_name', 'email', 'phone', 'company_name', 'source_platform')
    def _compute_summary(self):
        for rec in self:
            parts = []
            if rec.source_platform:
                parts.append(SOURCE_LABELS.get(rec.source_platform, rec.source_platform))
            if rec.company_name:
                parts.append(rec.company_name)
            if rec.email:
                parts.append(rec.email)
            if rec.phone:
                parts.append(rec.phone)
            try:
                data = json.loads(rec.fields_json or '{}')
                skip_norms = {
                    _norm_field_key(k)
                    for k in (_NAME_KEYS + _EMAIL_KEYS + _PHONE_KEYS + _COMPANY_KEYS)
                }
                for k, v in (data or {}).items():
                    if _norm_field_key(k) in skip_norms:
                        continue
                    parts.append(f'{k}: {v}')
            except Exception:
                pass
            rec.summary = ' | '.join(str(p) for p in parts[:8])

    @api.model
    def _resolve_source_from_ad(self, ad_id, item=None):
        """Resolve Instagram/Facebook/Meta from cached ad, remote payload, or explicit attributes."""
        item = item or {}
        explicit = (
            item.get('platform')
            or item.get('publisherPlatform')
            or item.get('publisher_platform')
            or item.get('channel')
            or item.get('source')
            or (item.get('ad') or {}).get('platform')
        )
        if isinstance(explicit, str):
            explicit = explicit.lower().strip()
            if explicit in ('ig', 'instagram', 'instagram_lead_gen'):
                return 'instagram', item.get('adName') or item.get('ad_name'), item.get('campaignName')
            if explicit in ('fb', 'facebook', 'facebook_lead_gen', 'messenger'):
                return 'facebook', item.get('adName') or item.get('ad_name'), item.get('campaignName')

        ad_name = item.get('adName') or item.get('ad_name') or False
        camp_name = item.get('campaignName') or item.get('campaign_name') or False
        creative = {}

        if ad_id:
            MetaAd = self.env['tcrm.marketing.meta.ad'].sudo()
            cached = MetaAd.search([('platform_ad_id', '=', str(ad_id))], limit=1)
            if cached and cached.source_platform in ('facebook', 'instagram'):
                return (
                    cached.source_platform,
                    cached.name,
                    cached.campaign_id.name if cached.campaign_id else camp_name,
                )
            # Skip remote ad lookup during bulk lead sync (rate-limit heavy)
            if not self.env.context.get('marketing_skip_creative'):
                # Try Zernio ad lookup
                try:
                    client = self.env['tcrm.marketing.profile']._get_zernio_client()
                    remote = client.get_ad(str(ad_id))
                    if remote:
                        creative = remote.get('creative') or {}
                        ad_name = ad_name or remote.get('name') or remote.get('adName')
                        camp_name = camp_name or remote.get('campaignName')
                        platform = detect_placement_platform(
                            name=ad_name or '',
                            campaign_name=camp_name or '',
                            creative=creative,
                        )
                        return platform, ad_name, camp_name
                except Exception:
                    pass

        # Check explicit naming in ad / campaign name
        text = f"{ad_name or ''} {camp_name or ''}".lower()
        if 'facebook' in text or r'\bfb\b' in text:
            if 'instagram' not in text:
                return 'facebook', ad_name, camp_name
        if 'instagram' in text or 'insta' in text:
            if 'facebook' not in text:
                return 'instagram', ad_name, camp_name

        platform = detect_placement_platform(
            name=ad_name or '',
            campaign_name=camp_name or '',
            creative=creative,
            explicit=None,
        )
        return platform, ad_name, camp_name

    @api.model
    def _fallback_source_for_form(self, form):
        """When ad is unknown, infer from form-named campaigns or fallback to Page platform."""
        Campaign = self.env['tcrm.marketing.campaign'].sudo()
        AdAccount = self.env['tcrm.marketing.ad.account'].sudo()
        form_token = (form.name or '').split('|')[0].strip()
        page_name = (form.account_id.name or '').strip()

        preferred_acts = AdAccount.search([
            ('account_id', '=', form.account_id.id),
            ('name', 'ilike', page_name[:20] if page_name else ''),
        ]) if page_name else AdAccount.browse()

        if preferred_acts:
            domain_base = [('ad_account_id', 'in', preferred_acts.ids)]
        else:
            domain_base = [
                '|',
                ('account_id', '=', form.account_id.id),
                ('ad_account_id.account_id', '=', form.account_id.id),
            ]

        camps = Campaign.search(
            domain_base + [
                '|', '|',
                ('name', 'ilike', 'instagram'),
                ('name', 'ilike', 'facebook'),
                ('name', 'ilike', 'form'),
            ],
            limit=80,
        )
        if form_token and len(form_token) >= 4:
            camps |= Campaign.search(
                domain_base + [('name', 'ilike', form_token[:24])],
                limit=40,
            )

        if camps:
            ig_hits = sum(1 for c in camps if c.platform == 'instagram' or 'instagram' in (c.name or '').lower())
            fb_hits = sum(1 for c in camps if c.platform == 'facebook' or 'facebook' in (c.name or '').lower())
            if ig_hits > fb_hits:
                return 'instagram'
            if fb_hits > ig_hits:
                return 'facebook'

        # Default fallback: Meta Lead Gen forms are Facebook-owned even when
        # pulled through a Meta Ads Zernio credential.
        if form and form.account_id:
            if form.account_id.platform in ('facebook', 'metaads'):
                return 'facebook'
            if form.account_id.platform == 'instagram':
                return 'instagram'
        return 'facebook'

    @api.model
    def _upsert_from_remote(self, item, form):
        lid = str(item.get('id') or item.get('leadgenId') or '')
        if not lid:
            return self.browse()
        fields_map = item.get('fields') or {}
        if not fields_map and item.get('fieldData'):
            fields_map = {}
            for row in item['fieldData']:
                name = row.get('name')
                vals = row.get('values') or []
                if name:
                    fields_map[name] = vals[0] if vals else ''
        ad_id = item.get('adId') and str(item.get('adId')) or False
        source, ad_name, camp_name = self._resolve_source_from_ad(ad_id, item)
        if source == 'meta' and not ad_name:
            source = self._fallback_source_for_form(form)
        contact = _extract_contact_from_fields(fields_map)
        vals = {
            'leadgen_id': lid,
            'form_id': form.id,
            'contact_name': contact['contact_name'],
            'email': contact['email'],
            'phone': contact['phone'],
            'company_name': contact['company_name'],
            'ad_id': ad_id,
            'ad_name': ad_name or False,
            'campaign_id_remote': item.get('campaignId') and str(item.get('campaignId')) or False,
            'campaign_name': camp_name or False,
            'source_platform': source,
            'created_time': _parse_meta_dt(item.get('createdTime')),
            'fields_json': json.dumps(fields_map, ensure_ascii=False, default=str)[:12000],
        }
        existing = self.search([('leadgen_id', '=', lid)], limit=1)
        if existing:
            existing.write(vals)
            return existing
        return self.create(vals)

    @api.model
    def _get_utm_source(self, platform_key):
        label = SOURCE_LABELS.get(platform_key) or 'Meta'
        UtmSource = self.env['utm.source'].sudo()
        source = UtmSource.search([('name', '=', label)], limit=1)
        if not source:
            source = UtmSource.search([('name', 'ilike', label)], limit=1)
        if not source:
            source = UtmSource.create({'name': label})
        return source

    def _sync_crm_source(self):
        """Update CRM lead source_id to match detected platform."""
        for rec in self:
            if not rec.crm_lead_id or not rec.source_platform:
                continue
            source = self._get_utm_source(rec.source_platform)
            label = SOURCE_LABELS.get(rec.source_platform, 'Meta')
            write_vals = {}
            if 'source_id' in rec.crm_lead_id._fields and rec.crm_lead_id.source_id != source:
                write_vals['source_id'] = source.id
            # Refresh description header with real source
            if 'description' in rec.crm_lead_id._fields:
                desc = rec.crm_lead_id.description or ''
                header = _(
                    'Kaynak: %(src)s\nMeta Lead Form: %(form)s\nReklam: %(ad)s\nAd ID: %(adid)s\nLead ID: %(lid)s'
                ) % {
                    'src': label,
                    'form': rec.form_id.name,
                    'ad': rec.ad_name or '-',
                    'adid': rec.ad_id or '-',
                    'lid': rec.leadgen_id,
                }
                # Keep field answers after blank line if present
                tail = ''
                if rec.summary:
                    # strip leading source label from summary for description body
                    bits = [b for b in (rec.summary or '').split(' | ') if b not in SOURCE_LABELS.values()]
                    tail = '\n\n' + ' | '.join(bits)
                write_vals['description'] = header + tail
            if write_vals:
                rec.crm_lead_id.sudo().write(write_vals)

    def action_reparse_contact_fields(self):
        """Re-extract name/email/phone from fields_json (locale form keys) and push to CRM."""
        records = self or self.search([])
        updated = 0
        for rec in records:
            try:
                data = json.loads(rec.fields_json or '{}')
            except Exception:
                data = {}
            contact = _extract_contact_from_fields(data)
            write_vals = {k: v for k, v in contact.items() if v}
            if not write_vals:
                continue
            rec.write(write_vals)
            updated += 1
            if rec.crm_lead_id:
                crm_vals = {}
                if contact['contact_name']:
                    # Replace placeholder "Meta Lead <id>" names with real contact
                    cur = rec.crm_lead_id.name or ''
                    if (not cur) or cur.startswith('Meta Lead ') or cur == rec.leadgen_id:
                        crm_vals['name'] = contact['contact_name']
                    crm_vals['contact_name'] = contact['contact_name']
                if contact['email']:
                    crm_vals['email_from'] = contact['email']
                if contact['phone']:
                    crm_vals['phone'] = contact['phone']
                if contact['company_name']:
                    crm_vals['partner_name'] = contact['company_name']
                if crm_vals:
                    rec.crm_lead_id.sudo().write(crm_vals)
        return updated

    def action_import_to_crm(self):
        CrmLead = self.env['crm.lead'].sudo()

        for rec in self:
            if rec.crm_lead_id:
                rec.state = 'imported'
                rec._sync_crm_source()
                # Keep CRM contact fields in sync when Meta lead was reparsed
                contact_vals = {}
                if rec.contact_name and (
                    not rec.crm_lead_id.contact_name
                    or (rec.crm_lead_id.name or '').startswith('Meta Lead ')
                ):
                    contact_vals['contact_name'] = rec.contact_name
                    if (rec.crm_lead_id.name or '').startswith('Meta Lead '):
                        contact_vals['name'] = rec.contact_name
                if rec.email and not rec.crm_lead_id.email_from:
                    contact_vals['email_from'] = rec.email
                if rec.phone and not rec.crm_lead_id.phone:
                    contact_vals['phone'] = rec.phone
                if contact_vals:
                    rec.crm_lead_id.sudo().write(contact_vals)
                continue
            # Re-resolve source in case ads were synced after lead pull
            if rec.ad_id:
                src, ad_name, camp_name = rec._resolve_source_from_ad(rec.ad_id)
                updates = {'source_platform': src}
                if ad_name:
                    updates['ad_name'] = ad_name
                if camp_name:
                    updates['campaign_name'] = camp_name
                if src == 'meta':
                    updates['source_platform'] = rec._fallback_source_for_form(rec.form_id)
                rec.write(updates)

            source = rec._get_utm_source(rec.source_platform or 'meta')
            label = SOURCE_LABELS.get(rec.source_platform or 'meta', 'Meta')
            # Contact name only — never prefix with [Instagram]/[Facebook]/[Meta]
            name = rec.contact_name or rec.email or rec.phone or _('Meta Lead %s') % rec.leadgen_id
            name = rec._strip_platform_prefix(name)
            vals = {
                'name': name,
                'contact_name': rec.contact_name or False,
                'email_from': rec.email or False,
                'phone': rec.phone or False,
                'partner_name': rec.company_name or False,
                # Auto-convert Meta leads to opportunities (no manual Convert step)
                'type': 'opportunity',
                'expected_revenue': 0.0,
                'description': _(
                    'Kaynak: %(src)s\nMeta Lead Form: %(form)s\nReklam: %(ad)s\nAd ID: %(adid)s\nLead ID: %(lid)s\n\n%(summary)s'
                ) % {
                    'src': label,
                    'form': rec.form_id.name,
                    'ad': rec.ad_name or '-',
                    'adid': rec.ad_id or '-',
                    'lid': rec.leadgen_id,
                    'summary': rec.summary or '',
                },
                'company_id': rec.company_id.id,
                'source_id': source.id,
            }
            # Oluşturma Tarihi = original Meta form fill time (not TCRM import time)
            if rec.created_time:
                vals['create_date'] = rec.created_time
            crm = CrmLead.with_context(tracking_disable=True).create(vals)
            if rec.created_time and crm.create_date != rec.created_time:
                # Fallback for ORM builds that ignore create_date in vals
                self.env.cr.execute(
                    'UPDATE crm_lead SET create_date = %s WHERE id = %s',
                    (fields.Datetime.to_string(rec.created_time), crm.id),
                )
                crm.invalidate_recordset(['create_date'])
            # Creative fetch hits Zernio heavily — skip during bulk lead sync
            if rec.ad_id and not self.env.context.get('marketing_skip_creative'):
                rec._ensure_ad_creative_cached(rec.ad_id)
            if 'crm.tag' in self.env:
                Tag = self.env['crm.tag'].sudo()
                tags = []
                for tag_name in ('Meta Lead', label):
                    tag = Tag.search([('name', '=', tag_name)], limit=1)
                    if not tag:
                        tag = Tag.create({'name': tag_name})
                    tags.append(tag.id)
                crm.write({'tag_ids': [(6, 0, list(dict.fromkeys(tags)))]})
            rec.write({'crm_lead_id': crm.id, 'state': 'imported'})
        return True

    @api.model
    def action_refresh_sources(self):
        """Re-detect source for all meta leads and push to CRM."""
        # Prefer having ads cached
        try:
            self.env['tcrm.marketing.campaign'].action_sync_from_zernio()
        except Exception as exc:
            _logger.warning('Campaign sync during source refresh: %s', exc)

        leads = self.search([])
        updated = 0
        for lead in leads:
            src, ad_name, camp_name = lead._resolve_source_from_ad(
                lead.ad_id,
                {
                    'adName': lead.ad_name,
                    'campaignName': lead.campaign_name,
                },
            )
            if src == 'meta':
                src = lead._fallback_source_for_form(lead.form_id)
            vals = {'source_platform': src}
            if ad_name:
                vals['ad_name'] = ad_name
            if camp_name:
                vals['campaign_name'] = camp_name
            lead.write(vals)
            if lead.crm_lead_id:
                lead._sync_crm_source()
                # Strip any legacy [Instagram]/[Facebook]/[Meta] name prefixes
                crm_name = lead.crm_lead_id.name or ''
                clean = lead._strip_platform_prefix(crm_name)
                write_crm = {}
                if clean != crm_name:
                    write_crm['name'] = clean
                if lead.crm_lead_id.type == 'lead':
                    write_crm['type'] = 'opportunity'
                if write_crm:
                    lead.crm_lead_id.sudo().write(write_crm)
            if lead.ad_id:
                lead._ensure_ad_creative_cached(lead.ad_id)
            updated += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Marketing Hub'),
                'message': _('%s lead kaynağı güncellendi (Instagram / Facebook / Meta).') % updated,
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def action_sync_all_forms(self, *, import_crm: bool = True, max_pages_per_form: int = 5):
        Form = self.env['tcrm.marketing.lead.form']
        Form.action_sync_from_zernio()
        Form._discover_lead_ad_sources()
        total = 0
        forms = Form.search([
            ('company_id', '=', self.env.company.id),
            ('account_id.active', '=', True),
            ('account_id.sync_enabled', '=', True),
            ('status', '!=', 'AD_SOURCE_INACTIVE'),
        ])
        for form in forms:
            try:
                total += form.action_sync_leads(
                    limit_pages=max_pages_per_form,
                    import_crm=import_crm,
                )
            except (ZernioError, UserError) as exc:
                _logger.warning(
                    'Skipping form %s during sync_all: %s',
                    form.zernio_form_id,
                    exc,
                )
                continue
        return total

    @api.model
    def _cron_sync_meta_leads_to_crm(self):
        """Scheduled: pull Meta lead forms/leads from Zernio and create CRM opportunities.

        Runs without requiring a manual Marketing Hub Sync click.
        Prefers the connected Meta Ads Zernio credential for lead pulls.
        """
        companies = self.env['res.company'].sudo().search([])
        grand_total = 0
        for company in companies:
            Lead = self.with_company(company).sudo()
            Account = self.env['tcrm.marketing.account'].with_company(company).sudo()
            try:
                Account.action_sync_from_zernio()
            except Exception as exc:
                _logger.warning(
                    'Marketing Hub account refresh failed company=%s: %s',
                    company.id,
                    exc,
                )
            try:
                pulled = Lead.action_sync_all_forms(
                    import_crm=True,
                    # Sources are newest-first. Two pages cover up to 100 new
                    # submissions per source/run without excessive API usage.
                    max_pages_per_form=2,
                )
                grand_total += int(pulled or 0)
                _logger.info(
                    'Marketing Hub auto Meta→CRM sync company=%s pulled=%s',
                    company.id,
                    pulled,
                )
            except Exception:
                _logger.exception(
                    'Marketing Hub auto Meta→CRM sync failed company=%s',
                    company.id,
                )
        return grand_total
