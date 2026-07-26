# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime

from tcrm import _, api, fields, models
from tcrm.exceptions import UserError

from ..services.zernio_client import ZernioError
from .marketing_ad import detect_placement_platform, extract_creative_preview

_logger = logging.getLogger(__name__)

SOURCE_LABELS = {
    'instagram': 'Instagram',
    'facebook': 'Facebook',
    'meta': 'Meta',
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
    def action_sync_from_zernio(self):
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        accounts = self.env['tcrm.marketing.account'].search([
            ('platform', '=', 'facebook'),
            ('active', '=', True),
            ('sync_enabled', '=', True),
            ('company_id', '=', self.env.company.id),
        ])
        synced = 0
        for social in accounts:
            try:
                data = client.list_lead_forms(account_id=social.zernio_id, limit=50)
            except ZernioError as exc:
                _logger.warning('Lead forms sync failed for %s: %s', social.zernio_id, exc)
                err = str(exc)
                # Never persist secrets if a misconfigured client echoes them
                for secret_key in ('api_key', 'apiKey', 'token', 'Bearer', 'authorization'):
                    if secret_key.lower() in err.lower():
                        err = _('Senkron hatası (ayrıntılar gizlendi).')
                        break
                social.sudo().write({'sync_error': err[:2000]})
                continue
            social.sudo().write({
                'sync_error': False,
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
                    self.sudo().create(vals)
                synced += 1
        return synced

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

        MetaLead = self.env['tcrm.marketing.meta.lead'].sudo()
        cursor = None
        created = 0
        for _ in range(limit_pages):
            data = client.list_form_leads(
                self.zernio_form_id,
                account_id=self.account_id.zernio_id,
                limit=50,
                cursor=cursor,
            )
            rows = data.get('leads') or []
            for item in rows:
                lead = MetaLead._upsert_from_remote(item, form=self)
                if lead:
                    created += 1
                    if import_crm and not lead.crm_lead_id:
                        lead.action_import_to_crm()
                    elif import_crm and lead.crm_lead_id:
                        lead._sync_crm_source()
            pagination = data.get('pagination') or {}
            cursor = pagination.get('cursor')
            if not pagination.get('hasMore') or not cursor:
                break
        self.last_sync_at = fields.Datetime.now()
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
    )
    creative_image_url = fields.Char(
        string='Kreatif Görsel',
        compute='_compute_creative_preview',
    )
    creative_video_url = fields.Char(
        string='Kreatif Video',
        compute='_compute_creative_preview',
    )
    creative_thumbnail_url = fields.Char(
        string='Kreatif Önizleme',
        compute='_compute_creative_preview',
    )
    creative_body = fields.Text(
        string='Kreatif Metin',
        compute='_compute_creative_preview',
    )
    creative_permalink = fields.Char(
        string='Kreatif Bağlantı',
        compute='_compute_creative_preview',
    )
    creative_html = fields.Html(
        string='Kreatif Önizleme',
        compute='_compute_creative_preview',
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
            from markupsafe import escape, Markup

            media_type = preview.get('media_type') or 'none'
            image_url = preview.get('image_url') or ''
            thumb = preview.get('thumbnail_url') or image_url or ''
            video_url = preview.get('video_url') or ''
            permalink = preview.get('permalink') or preview.get('link_url') or ''
            body = preview.get('body') or ''
            rec.creative_media_type = media_type
            rec.creative_image_url = image_url or False
            rec.creative_video_url = video_url or False
            rec.creative_thumbnail_url = thumb or False
            rec.creative_body = body or False
            rec.creative_permalink = permalink or False
            parts = []
            if media_type == 'video' and (thumb or video_url):
                href = escape(video_url or permalink or thumb)
                img = escape(thumb or '')
                parts.append(
                    f'<div style="margin-bottom:8px">'
                    f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
                    f'background:#ede9fe;color:#6d28d9;font-size:12px;font-weight:600">'
                    f'VİDEO / REEL</span></div>'
                )
                if thumb:
                    parts.append(
                        f'<a href="{href}" target="_blank" rel="noopener">'
                        f'<img src="{img}" alt="Video kreatif" '
                        f'style="max-height:280px;max-width:100%;border-radius:8px;object-fit:contain"/>'
                        f'</a>'
                    )
                elif video_url:
                    parts.append(
                        f'<video controls style="max-height:280px;max-width:100%;border-radius:8px">'
                        f'<source src="{escape(video_url)}"/></video>'
                    )
            elif media_type == 'image' and thumb:
                parts.append(
                    f'<div style="margin-bottom:8px">'
                    f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
                    f'background:#cffafe;color:#0e7490;font-size:12px;font-weight:600">'
                    f'GÖRSEL</span></div>'
                    f'<img src="{escape(thumb)}" alt="Görsel kreatif" '
                    f'style="max-height:280px;max-width:100%;border-radius:8px;object-fit:contain"/>'
                )
            elif permalink:
                parts.append(
                    f'<div style="margin-bottom:8px">'
                    f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
                    f'background:#fce7f3;color:#9d174d;font-size:12px;font-weight:600">'
                    f'INSTAGRAM / FACEBOOK</span></div>'
                    f'<p><a class="btn btn-sm btn-primary" href="{escape(permalink)}" '
                    f'target="_blank" rel="noopener">Orijinal gönderiyi / reeli aç</a></p>'
                )
            else:
                parts.append(
                    '<p style="color:#64748b">Kreatif önizleme yok. '
                    'Kampanyaları senkronize ederek reklam kreatifini yükleyin.</p>'
                )
            if body:
                parts.append(
                    f'<p style="margin-top:10px;white-space:pre-wrap">{escape(body)}</p>'
                )
            if permalink and media_type != 'link':
                parts.append(
                    f'<p><a href="{escape(permalink)}" target="_blank" rel="noopener">'
                    f'Orijinal gönderiyi aç</a></p>'
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
                for k, v in (data or {}).items():
                    if k in ('full_name', 'email', 'phone_number', 'şirket_adı'):
                        continue
                    parts.append(f'{k}: {v}')
            except Exception:
                pass
            rec.summary = ' | '.join(str(p) for p in parts[:8])

    @api.model
    def _resolve_source_from_ad(self, ad_id, item=None):
        """Resolve Instagram/Facebook/Meta from cached ad, remote payload, or heuristics."""
        item = item or {}
        explicit = (
            item.get('platform')
            or item.get('publisherPlatform')
            or item.get('publisher_platform')
            or (item.get('ad') or {}).get('platform')
        )
        if isinstance(explicit, str):
            explicit = explicit.lower().strip()
            if explicit in ('ig', 'instagram'):
                return 'instagram', item.get('adName') or item.get('ad_name'), item.get('campaignName')
            if explicit in ('fb', 'facebook'):
                return 'facebook', item.get('adName') or item.get('ad_name'), item.get('campaignName')

        ad_name = item.get('adName') or item.get('ad_name') or False
        camp_name = item.get('campaignName') or item.get('campaign_name') or False
        creative = {}

        if ad_id:
            MetaAd = self.env['tcrm.marketing.meta.ad'].sudo()
            cached = MetaAd.search([('platform_ad_id', '=', str(ad_id))], limit=1)
            if cached:
                return (
                    cached.source_platform or 'meta',
                    cached.name,
                    cached.campaign_id.name if cached.campaign_id else camp_name,
                )
            # Try Zernio ad lookup (works for synced ads / alternate ID dialects)
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
            except ZernioError:
                pass

        # Heuristic from any names present on the lead payload / form
        platform = detect_placement_platform(
            name=ad_name or '',
            campaign_name=camp_name or '',
            creative=creative,
            explicit=None,
        )
        return platform, ad_name, camp_name

    @api.model
    def _fallback_source_for_form(self, form):
        """When ad is unknown, infer from form-named campaigns on the same page."""
        Campaign = self.env['tcrm.marketing.campaign'].sudo()
        AdAccount = self.env['tcrm.marketing.ad.account'].sudo()
        form_token = (form.name or '').split('|')[0].strip()
        page_name = (form.account_id.name or '').strip()
        # Prefer the ad account that matches the Page name (e.g. Model Sanayi Merkezi)
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
                '|', '|', '|',
                ('name', 'ilike', 'form'),
                ('name', 'ilike', 'story'),
                ('name', 'ilike', 'instagram'),
                ('name', 'ilike', 'facebook'),
            ],
            limit=80,
        )
        if form_token and len(form_token) >= 4:
            camps |= Campaign.search(
                domain_base + [('name', 'ilike', form_token[:24])],
                limit=40,
            )
        if not camps:
            return 'meta'
        ig_hits = sum(
            1 for c in camps
            if c.platform == 'instagram'
            or 'instagram' in (c.name or '').lower()
            or (
                'story' in (c.name or '').lower()
                and 'facebook' not in (c.name or '').lower()
            )
        )
        fb_hits = sum(
            1 for c in camps
            if c.platform == 'facebook'
            or (
                'facebook' in (c.name or '').lower()
                and 'instagram' not in (c.name or '').lower()
            )
        )
        if ig_hits and ig_hits > fb_hits:
            return 'instagram'
        if fb_hits and fb_hits > ig_hits:
            return 'facebook'
        return 'meta'

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
        vals = {
            'leadgen_id': lid,
            'form_id': form.id,
            'contact_name': fields_map.get('full_name') or fields_map.get('FULL_NAME') or False,
            'email': fields_map.get('email') or fields_map.get('EMAIL') or False,
            'phone': fields_map.get('phone_number') or fields_map.get('PHONE') or False,
            'company_name': fields_map.get('şirket_adı')
            or fields_map.get('company_name')
            or fields_map.get('COMPANY_NAME')
            or False,
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

    def action_import_to_crm(self):
        CrmLead = self.env['crm.lead'].sudo()

        for rec in self:
            if rec.crm_lead_id:
                rec.state = 'imported'
                rec._sync_crm_source()
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
            crm = CrmLead.create(vals)
            # Ensure creative is fetched for this ad (image / video / reel)
            if rec.ad_id:
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
        total = 0
        forms = Form.search([
            ('company_id', '=', self.env.company.id),
            ('account_id.active', '=', True),
            ('account_id.sync_enabled', '=', True),
        ])
        for form in forms:
            total += form.action_sync_leads(
                limit_pages=max_pages_per_form,
                import_crm=import_crm,
            )
        return total
