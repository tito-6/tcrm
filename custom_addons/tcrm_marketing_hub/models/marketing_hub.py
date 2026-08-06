# -*- coding: utf-8 -*-
"""Server methods for the Marketing Hub OWL application."""
from collections import defaultdict
from datetime import datetime, time, timedelta

from tcrm import _, api, fields, models
from tcrm.exceptions import AccessError, UserError

from ..services.zernio_client import ZernioError
from .marketing_ad import extract_creative_preview

SOURCE_LABELS = {
    'instagram': 'Instagram',
    'facebook': 'Facebook',
    'meta': 'Meta',
    'google': 'Google Ads',
}

STATE_LABELS = {
    'new': 'Yeni',
    'imported': 'CRM’e Aktarıldı',
    'skipped': 'Atlandı',
}


class MarketingHub(models.AbstractModel):
    _name = 'tcrm.marketing.hub'
    _description = 'Marketing Hub Dashboard API'

    @api.model
    def _parse_date_bound(self, value, end=False):
        """Accept YYYY-MM-DD or datetime string → naive datetime bound."""
        if not value:
            return False
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        if len(text) == 10:
            day = fields.Date.to_date(text)
            return datetime.combine(day, time.max if end else time.min)
        try:
            return fields.Datetime.to_datetime(text)
        except Exception:
            return False

    @api.model
    def _lead_domain(self, company, date_from=None, date_to=None, source=None):
        domain = [('company_id', '=', company.id)]
        dt_from = self._parse_date_bound(date_from, end=False)
        dt_to = self._parse_date_bound(date_to, end=True)
        if dt_from:
            domain.append(('created_time', '>=', fields.Datetime.to_string(dt_from)))
        if dt_to:
            domain.append(('created_time', '<=', fields.Datetime.to_string(dt_to)))
        if source and source in ('instagram', 'facebook', 'meta'):
            domain.append(('source_platform', '=', source))
        return domain

    @api.model
    def _campaign_domain(self, company, selected=None, date_from=None, date_to=None):
        """Campaign list domain. Match all ad-account rows that share the same act id.

        Duplicate Meta ad-account records (facebook/metaads) often exist for one act_*;
        campaigns are usually attached to only one of them.
        """
        domain = [('company_id', '=', company.id)]
        if selected:
            act = (selected.meta_act_id or '').strip()
            if act:
                siblings = self.env['tcrm.marketing.ad.account'].sudo().search([
                    ('company_id', '=', company.id),
                    ('meta_act_id', '=', act),
                    ('provider', '!=', 'google'),
                ])
                domain.append(('ad_account_id', 'in', siblings.ids or [selected.id]))
            else:
                domain.append(('ad_account_id', '=', selected.id))
        # Do not filter hub campaign cards by last_sync_at — date bar is for leads/metrics.
        return domain

    @api.model
    def _dedupe_ad_accounts_for_selector(self, ad_accounts):
        """One selector row per meta_act_id, preferring the row that owns the most campaigns."""
        Campaign = self.env['tcrm.marketing.campaign'].sudo()
        best_by_act = {}
        for acc in ad_accounts:
            act = (acc.meta_act_id or f'id:{acc.id}').strip()
            camp_count = Campaign.search_count([
                ('ad_account_id', '=', acc.id),
                ('platform', '!=', 'google'),
            ])
            prev = best_by_act.get(act)
            if not prev or camp_count > prev[0]:
                best_by_act[act] = (camp_count, acc)
        # Stable-ish order by name
        return self.env['tcrm.marketing.ad.account'].browse(
            [pair[1].id for pair in sorted(best_by_act.values(), key=lambda p: (p[1].name or '').lower())]
        )

    @api.model
    def _creative_for_lead(self, lead=None, ad_id=None, ad_name=None, campaign_name=None):
        """Resolve creative from cached Meta ads (ID, then name / campaign)."""
        MetaAd = self.env['tcrm.marketing.meta.ad'].sudo()
        if lead:
            ad_id = ad_id or lead.ad_id
            ad_name = ad_name or lead.ad_name
            campaign_name = campaign_name or lead.campaign_name
        cached = MetaAd.browse()
        if ad_id:
            cached = MetaAd.search([('platform_ad_id', '=', str(ad_id))], limit=1)
        if not cached and ad_name:
            cached = MetaAd.search([('name', '=ilike', ad_name)], limit=1)
        if not cached and ad_name and len(ad_name) >= 8:
            cached = MetaAd.search([('name', 'ilike', ad_name[:24])], limit=1)
        if not cached and campaign_name:
            Campaign = self.env['tcrm.marketing.campaign'].sudo()
            camp = Campaign.search([
                '|',
                ('name', '=ilike', campaign_name),
                ('platform_campaign_id', '=', str(getattr(lead, 'campaign_id_remote', '') or '')),
            ], limit=1) if lead else Campaign.search([('name', '=ilike', campaign_name)], limit=1)
            if camp and camp.meta_ad_ids:
                cached = camp.meta_ad_ids[:1]
        if cached:
            return cached.get_creative_preview()
        return extract_creative_preview({})

    @api.model
    def _serialize_campaign_row(self, c):
        adsets = []
        for aset in c.adset_ids:
            ads = []
            for ad in aset.ad_ids:
                ads.append({
                    'id': ad.id,
                    'name': ad.name,
                    'platform_ad_id': ad.platform_ad_id,
                    'status': ad.status or 'ACTIVE',
                    'creative_type': ad.creative_media_type or 'none',
                    'creative_thumb': ad.creative_thumbnail_url or ad.creative_image_url or '',
                    'creative_title': ad.creative_title or '',
                    'creative_body': (ad.creative_body or '')[:200],
                    'creative_html': ad.creative_html or '',
                    'spend': ad.spend or 0.0,
                    'impressions': ad.impressions or 0,
                    'clicks': ad.clicks or 0,
                    'meta_ads_manager_url': ad.meta_ads_manager_url or '',
                })
            adsets.append({
                'id': aset.id,
                'name': aset.name,
                'platform_adset_id': aset.platform_adset_id,
                'status': aset.status or 'ACTIVE',
                'daily_budget': aset.daily_budget or 0.0,
                'spend': aset.spend or 0.0,
                'impressions': aset.impressions or 0,
                'clicks': aset.clicks or 0,
                'ads': ads,
            })

        direct_ads = []
        for ad in c.meta_ad_ids.filtered(lambda a: not a.adset_id):
            direct_ads.append({
                'id': ad.id,
                'name': ad.name,
                'platform_ad_id': ad.platform_ad_id,
                'status': ad.status or 'ACTIVE',
                'creative_type': ad.creative_media_type or 'none',
                'creative_thumb': ad.creative_thumbnail_url or ad.creative_image_url or '',
                'creative_title': ad.creative_title or '',
                'creative_body': (ad.creative_body or '')[:200],
                'creative_html': ad.creative_html or '',
                'spend': ad.spend or 0.0,
                'impressions': ad.impressions or 0,
                'clicks': ad.clicks or 0,
                'meta_ads_manager_url': ad.meta_ads_manager_url or '',
            })

        act_clean = (
            c.ad_account_id.meta_act_id.replace('act_', '')
            if c.ad_account_id and c.ad_account_id.meta_act_id
            else ''
        )
        if c.platform == 'google':
            manager_url = (
                f'https://ads.google.com/aw/campaigns?campaignId={c.platform_campaign_id}'
                if c.platform_campaign_id else 'https://ads.google.com/'
            )
        else:
            manager_url = (
                f'https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={act_clean}&selected_campaign_ids={c.platform_campaign_id}'
                if act_clean and c.platform_campaign_id
                else ''
            )

        return {
            'id': c.id,
            'name': c.name,
            'platform_campaign_id': c.platform_campaign_id or '',
            'status': c.status,
            'platform': SOURCE_LABELS.get(c.platform, c.platform or 'Meta'),
            'platform_key': c.platform or 'meta',
            'channel_type': c.channel_type or '',
            'spend': c.spend,
            'impressions': c.impressions,
            'clicks': c.clicks,
            'conversions': c.conversions,
            'roas': c.roas,
            'currency': c.currency or '',
            'budget': c.budget_amount,
            'budget_type': c.budget_type or '',
            'ad_account': c.ad_account_id.name if c.ad_account_id else '',
            'adset_count': len(c.adset_ids),
            'ad_count': len(c.meta_ad_ids),
            'adsets': adsets,
            'direct_ads': direct_ads,
            'meta_ads_manager_url': manager_url,
            'ads_manager_url': manager_url,
            'last_sync_at': fields.Datetime.to_string(c.last_sync_at) if c.last_sync_at else '',
        }

    @api.model
    def _serialize_lead_row(self, lead, include_creative=False):
        creative = self._creative_for_lead(lead)
        row = {
            'id': lead.id,
            'name': lead.contact_name or lead.email or lead.leadgen_id,
            'email': lead.email or '',
            'phone': lead.phone or '',
            'company': lead.company_name or '',
            'form': lead.form_id.name,
            'form_id': lead.form_id.id,
            'ad_id': lead.ad_id or '',
            'ad_name': lead.ad_name or '',
            'campaign_id_remote': lead.campaign_id_remote or '',
            'campaign_name': lead.campaign_name or '',
            'source': SOURCE_LABELS.get(lead.source_platform, 'Meta'),
            'source_platform': lead.source_platform or 'meta',
            'created_time': fields.Datetime.to_string(lead.created_time) if lead.created_time else '',
            'created_time_display': fields.Datetime.context_timestamp(
                lead, lead.created_time
            ).strftime('%d.%m.%Y %H:%M') if lead.created_time else '',
            'state': lead.state,
            'state_label': STATE_LABELS.get(lead.state, lead.state or ''),
            'crm_lead_id': lead.crm_lead_id.id if lead.crm_lead_id else False,
            'summary': lead.summary or '',
            'leadgen_id': lead.leadgen_id or '',
            'account': lead.account_id.name if lead.account_id else '',
            'creative_type': creative.get('media_type') or 'none',
            'creative_thumb': (
                creative.get('thumbnail_url') or creative.get('image_url') or ''
            )[:500],
        }
        if include_creative:
            row['creative'] = creative
        return row

    @api.model
    def get_dashboard(self, selected_ad_account_id=None, date_from=None, date_to=None, lead_source=None):
        """Payload for the full-page Marketing Hub UI."""
        company = self.env.company
        ICP = self.env['ir.config_parameter'].sudo()
        if selected_ad_account_id:
            ICP.set_param(
                f'tcrm_marketing_hub.selected_ad_account.{company.id}',
                str(selected_ad_account_id),
            )
        else:
            raw = ICP.get_param(f'tcrm_marketing_hub.selected_ad_account.{company.id}')
            selected_ad_account_id = int(raw) if raw and str(raw).isdigit() else False

        accounts = self.env['tcrm.marketing.account'].search([
            ('company_id', '=', company.id),
            ('active', '=', True),
        ])
        ad_accounts = self.env['tcrm.marketing.ad.account'].search([
            ('company_id', '=', company.id),
            ('active', '=', True),
            ('provider', '!=', 'google'),
        ])
        ad_accounts = self._dedupe_ad_accounts_for_selector(ad_accounts)
        selected = ad_accounts.filtered(lambda a: a.id == selected_ad_account_id)[:1]
        if not selected and selected_ad_account_id:
            # User may have had a duplicate sibling selected — map by act id
            raw_sel = self.env['tcrm.marketing.ad.account'].browse(int(selected_ad_account_id))
            if raw_sel.exists() and raw_sel.meta_act_id:
                selected = ad_accounts.filtered(lambda a: a.meta_act_id == raw_sel.meta_act_id)[:1]
        if not selected and ad_accounts:
            # Prefer Perla / highest campaign count account
            selected = ad_accounts.sorted(
                key=lambda a: self.env['tcrm.marketing.campaign'].sudo().search_count([
                    ('ad_account_id', 'in', self.env['tcrm.marketing.ad.account'].sudo().search([
                        ('meta_act_id', '=', a.meta_act_id),
                        ('company_id', '=', company.id),
                    ]).ids),
                    ('platform', '!=', 'google'),
                ]),
                reverse=True,
            )[:1] or ad_accounts[:1]
            selected_ad_account_id = selected.id

        forms = self.env['tcrm.marketing.lead.form'].search([
            ('company_id', '=', company.id),
        ])
        lead_domain = self._lead_domain(company, date_from, date_to, lead_source)
        meta_leads = self.env['tcrm.marketing.meta.lead'].search(lead_domain, limit=100)

        campaign_domain = self._campaign_domain(company, selected, date_from, date_to)
        campaign_domain = list(campaign_domain) + [('platform', '!=', 'google')]
        campaigns = self.env['tcrm.marketing.campaign'].search(
            campaign_domain, order='spend desc, id desc', limit=120,
        )
        if not campaigns and selected:
            # Last resort: any Meta campaign on sibling act rows (ignore stale selected id)
            campaigns = self.env['tcrm.marketing.campaign'].search(
                self._campaign_domain(company, selected) + [('platform', '!=', 'google')],
                order='spend desc, id desc',
                limit=120,
            )

        conversations = self.env['tcrm.marketing.conversation'].search([
            ('company_id', '=', company.id),
        ], limit=20)
        posts = self.env['tcrm.marketing.post'].search([
            ('company_id', '=', company.id),
        ], limit=20)

        analytics = self.env['tcrm.marketing.analytics'].search([
            ('company_id', '=', company.id),
        ], limit=1)

        base_lead = [('company_id', '=', company.id)]
        dated_lead = self._lead_domain(company, date_from, date_to)
        source_counts = {
            'instagram': self.env['tcrm.marketing.meta.lead'].search_count(
                dated_lead + [('source_platform', '=', 'instagram')]
            ),
            'facebook': self.env['tcrm.marketing.meta.lead'].search_count(
                dated_lead + [('source_platform', '=', 'facebook')]
            ),
            'meta': self.env['tcrm.marketing.meta.lead'].search_count(
                dated_lead + [('source_platform', '=', 'meta')]
            ),
        }
        pending_crm = self.env['tcrm.marketing.meta.lead'].search_count(
            dated_lead + [('crm_lead_id', '=', False)]
        )

        charts = self.get_lead_charts(
            date_from=date_from,
            date_to=date_to,
            selected_ad_account_id=selected_ad_account_id,
        )

        return {
            'selected_ad_account_id': selected_ad_account_id or False,
            'date_from': date_from or False,
            'date_to': date_to or False,
            'stats': {
                'accounts': len(accounts),
                'ad_accounts': len(ad_accounts),
                'forms': len(forms),
                'meta_leads': self.env['tcrm.marketing.meta.lead'].search_count(dated_lead),
                'meta_leads_all': self.env['tcrm.marketing.meta.lead'].search_count(base_lead),
                'crm_imported': self.env['tcrm.marketing.meta.lead'].search_count(
                    dated_lead + [('crm_lead_id', '!=', False)]
                ),
                'pending_crm': pending_crm,
                'conversations': self.env['tcrm.marketing.conversation'].search_count([
                    ('company_id', '=', company.id),
                ]),
                'campaigns': self.env['tcrm.marketing.campaign'].search_count([
                    ('company_id', '=', company.id),
                ]),
                'campaigns_selected': len(campaigns) if selected else 0,
                'posts': self.env['tcrm.marketing.post'].search_count([
                    ('company_id', '=', company.id),
                ]),
                'form_leads_meta_total': sum(forms.mapped('leads_count')),
                'source_instagram': source_counts['instagram'],
                'source_facebook': source_counts['facebook'],
                'source_meta': source_counts['meta'],
            },
            'accounts': [{
                'id': a.id,
                'name': a.name,
                'platform': a.platform,
                'username': a.username,
                'status': a.status,
                'followers': a.follower_count,
                'avatar_url': a.avatar_url or '',
                'sync_enabled': a.sync_enabled,
                'sync_error': a.sync_error or '',
                'last_sync_at': fields.Datetime.to_string(a.last_sync_at) if a.last_sync_at else '',
                'zernio_id': a.zernio_id,
            } for a in accounts],
            'ad_accounts': [{
                'id': a.id,
                'name': a.name,
                'meta_act_id': a.meta_act_id,
                'provider': a.provider or 'meta',
                'currency': a.currency or '',
                'business_name': a.business_name or '',
                'timezone': a.timezone_name or '',
                'min_budget': a.minimum_daily_budget,
                'social_account': a.account_id.display_name,
            } for a in ad_accounts],
            'forms': [{
                'id': f.id,
                'name': f.name,
                'status': f.status or '',
                'leads_count': f.leads_count,
                'imported': f.imported_lead_count,
                'account': f.account_id.name,
            } for f in forms],
            'leads': [self._serialize_lead_row(l) for l in meta_leads],
            'campaigns': [self._serialize_campaign_row(c) for c in campaigns],
            'conversations': [{
                'id': c.id,
                'name': c.name,
                'platform': c.platform,
                'participant_username': c.participant_username or '',
                'participant_picture': c.participant_picture or '',
                'avatar_url': c.avatar_url or c.participant_picture or '',
                'last_message': (c.last_message or '')[:120],
                'last_message_at': fields.Datetime.to_string(c.last_message_at) if c.last_message_at else '',
            } for c in conversations],
            'posts': [{
                'id': p.id,
                'name': p.name,
                'status': p.status,
                'platforms': p.platform_labels or '',
                'media_url': (p.media_urls or '').split('\n')[0].strip() if p.media_urls else '',
                'platform_url': p.platform_post_url or '',
            } for p in posts],
            'analytics': {
                'total_posts': analytics.total_posts if analytics else 0,
                'published_posts': analytics.published_posts if analytics else 0,
                'scheduled_posts': analytics.scheduled_posts if analytics else 0,
                'sync_at': fields.Datetime.to_string(analytics.sync_at) if analytics else '',
            },
            'charts': charts,
            'selected_ad_account': {
                'id': selected.id,
                'name': selected.name,
                'meta_act_id': selected.meta_act_id,
                'currency': selected.currency or '',
                'business_name': selected.business_name or '',
            } if selected else None,
        }

    @api.model
    def get_lead_detail(self, lead_id):
        """Full lead payload for hub side panel preview."""
        lead = self.env['tcrm.marketing.meta.lead'].browse(int(lead_id)).exists()
        if not lead:
            raise UserError(_('Lead bulunamadı.'))
        data = self._serialize_lead_row(lead, include_creative=True)
        field_answers = []
        try:
            raw = json_loads_safe(lead.fields_json)
            for key, val in (raw or {}).items():
                field_answers.append({'key': str(key), 'value': str(val)})
        except Exception:
            field_answers = []
        data['field_answers'] = field_answers
        data['page_name'] = lead.account_id.name if lead.account_id else ''
        data['form_status'] = lead.form_id.status or ''
        # Try live creative refresh if cache empty
        creative = data.get('creative') or {}
        if creative.get('media_type') == 'none' and lead.ad_id:
            try:
                client = self.env['tcrm.marketing.profile']._get_zernio_client()
                remote = client.get_ad(str(lead.ad_id))
                if remote:
                    creative = extract_creative_preview(remote.get('creative') or {})
                    data['creative'] = creative
                    data['creative_type'] = creative.get('media_type') or 'none'
                    data['creative_thumb'] = (
                        creative.get('thumbnail_url') or creative.get('image_url') or ''
                    )
                    if remote.get('name') and not data.get('ad_name'):
                        data['ad_name'] = remote.get('name')
                    # Cache for next time
                    MetaAd = self.env['tcrm.marketing.meta.ad'].sudo()
                    if not MetaAd.search([('platform_ad_id', '=', str(lead.ad_id))], limit=1):
                        MetaAd.create({
                            'name': remote.get('name') or lead.ad_name or str(lead.ad_id),
                            'platform_ad_id': str(lead.ad_id),
                            'source_platform': lead.source_platform or 'meta',
                            'company_id': lead.company_id.id,
                            'creative_json': __import__('json').dumps(
                                remote.get('creative') or {}, ensure_ascii=False, default=str
                            )[:8000],
                            'last_sync_at': fields.Datetime.now(),
                        })
            except Exception:
                pass
        return data

    @api.model
    def get_lead_charts(self, date_from=None, date_to=None, selected_ad_account_id=None):
        """Aggregations for donut / column charts."""
        company = self.env.company
        Lead = self.env['tcrm.marketing.meta.lead']
        domain = self._lead_domain(company, date_from, date_to)
        leads = Lead.search(domain, limit=5000)

        by_source = defaultdict(int)
        by_state = defaultdict(int)
        by_day = defaultdict(int)
        by_form = defaultdict(int)
        by_campaign = defaultdict(int)
        by_creative = defaultdict(int)

        for lead in leads:
            by_source[lead.source_platform or 'meta'] += 1
            by_state[lead.state or 'new'] += 1
            if lead.created_time:
                by_day[lead.created_time.strftime('%Y-%m-%d')] += 1
            if lead.form_id:
                by_form[lead.form_id.name or 'Form'] += 1
            camp = lead.campaign_name or 'Kampanya yok'
            by_campaign[camp] += 1
            creative = self._creative_for_lead(lead)
            by_creative[creative.get('media_type') or 'none'] += 1

        def _sorted_pairs(mapping, limit=12):
            items = sorted(mapping.items(), key=lambda x: (-x[1], x[0]))[:limit]
            return {
                'labels': [k for k, _ in items],
                'values': [v for _, v in items],
            }

        source_labels = [SOURCE_LABELS.get(k, k) for k in ('instagram', 'facebook', 'meta')]
        source_values = [
            by_source.get('instagram', 0),
            by_source.get('facebook', 0),
            by_source.get('meta', 0),
        ]

        # Fill missing days in range for smoother line/column chart
        day_keys = sorted(by_day.keys())
        if date_from and date_to and day_keys:
            start = fields.Date.to_date(str(date_from)[:10])
            end = fields.Date.to_date(str(date_to)[:10])
            filled = {}
            cur = start
            while cur <= end:
                key = cur.isoformat()
                filled[key] = by_day.get(key, 0)
                cur += timedelta(days=1)
            by_day = filled
            day_keys = sorted(by_day.keys())

        day_labels = [fields.Date.to_date(d).strftime('%d.%m') for d in day_keys[-30:]]
        day_values = [by_day[d] for d in day_keys[-30:]]

        form_chart = _sorted_pairs(by_form, 8)
        camp_chart = _sorted_pairs(by_campaign, 8)

        spend_labels, spend_values = [], []
        camp_domain = [('company_id', '=', company.id), ('platform', '!=', 'google')]
        if selected_ad_account_id:
            sel = self.env['tcrm.marketing.ad.account'].browse(int(selected_ad_account_id))
            if sel.exists():
                camp_domain = self._campaign_domain(company, sel) + [('platform', '!=', 'google')]
        top_camps = self.env['tcrm.marketing.campaign'].search(
            camp_domain, order='spend desc', limit=8
        )
        for c in top_camps:
            spend_labels.append((c.name or '')[:28])
            spend_values.append(round(c.spend or 0, 2))

        # Per-creative / per-ad lead attribution for Kreatif report
        creative_assets = {}
        for lead in leads:
            preview = self._creative_for_lead(lead)
            media = preview.get('media_type') or 'none'
            thumb = preview.get('thumbnail_url') or preview.get('image_url') or ''
            key = str(lead.ad_id or '') or thumb or (lead.ad_name or 'unknown')
            if key not in creative_assets:
                creative_assets[key] = {
                    'ad_id': lead.ad_id or '',
                    'ad_name': lead.ad_name or 'Reklam yok',
                    'campaign_name': lead.campaign_name or '',
                    'media_type': media,
                    'thumbnail_url': thumb,
                    'image_url': preview.get('image_url') or thumb,
                    'video_url': preview.get('video_url') or '',
                    'permalink': preview.get('permalink') or '',
                    'body': (preview.get('body') or '')[:160],
                    'leads': 0,
                    'imported': 0,
                }
            creative_assets[key]['leads'] += 1
            if lead.state == 'imported' or lead.crm_lead_id:
                creative_assets[key]['imported'] += 1
            # Prefer richer media if later lead has it
            if media in ('image', 'video') and creative_assets[key]['media_type'] in ('none', 'link'):
                creative_assets[key]['media_type'] = media
            if thumb and not creative_assets[key]['thumbnail_url']:
                creative_assets[key]['thumbnail_url'] = thumb

        creative_rows = sorted(
            creative_assets.values(),
            key=lambda r: (-r['leads'], r['ad_name'] or ''),
        )[:24]

        # Campaign performance table (leads + spend)
        camp_perf = {}
        for lead in leads:
            cname = lead.campaign_name or 'Kampanya yok'
            if cname not in camp_perf:
                camp_perf[cname] = {'name': cname, 'leads': 0, 'imported': 0, 'spend': 0.0}
            camp_perf[cname]['leads'] += 1
            if lead.state == 'imported' or lead.crm_lead_id:
                camp_perf[cname]['imported'] += 1
        for c in top_camps:
            name = c.name or 'Kampanya'
            if name not in camp_perf:
                camp_perf[name] = {'name': name, 'leads': 0, 'imported': 0, 'spend': 0.0}
            camp_perf[name]['spend'] = round(c.spend or 0, 2)
            camp_perf[name]['impressions'] = int(c.impressions or 0)
            camp_perf[name]['clicks'] = int(c.clicks or 0)
            camp_perf[name]['status'] = c.status or ''
        campaign_rows = sorted(
            camp_perf.values(),
            key=lambda r: (-r['leads'], -r.get('spend', 0)),
        )[:20]

        return {
            'by_source': {
                'labels': source_labels,
                'values': source_values,
                'colors': ['#db2777', '#2563eb', '#0f766e'],
            },
            'by_state': {
                'labels': [STATE_LABELS.get(k, k) for k in ('new', 'imported', 'skipped')],
                'values': [
                    by_state.get('new', 0),
                    by_state.get('imported', 0),
                    by_state.get('skipped', 0),
                ],
                'colors': ['#ca8a04', '#16a34a', '#94a3b8'],
            },
            'by_day': {
                'labels': day_labels,
                'values': day_values,
            },
            'by_form': form_chart,
            'by_campaign': camp_chart,
            'by_creative': {
                'labels': [
                    {'none': 'Kreatif yok', 'image': 'Görsel', 'video': 'Video'}.get(k, k)
                    for k in ('video', 'image', 'none')
                ],
                'values': [
                    by_creative.get('video', 0),
                    by_creative.get('image', 0),
                    by_creative.get('none', 0),
                ],
                'colors': ['#7c3aed', '#0891b2', '#94a3b8'],
            },
            'campaign_spend': {
                'labels': spend_labels,
                'values': spend_values,
            },
            'creative_rows': creative_rows,
            'campaign_rows': campaign_rows,
            'total_leads': len(leads),
            'kpis': {
                'total_leads': len(leads),
                'imported': by_state.get('imported', 0),
                'pending': by_state.get('new', 0),
                'skipped': by_state.get('skipped', 0),
                'import_rate': round(100.0 * by_state.get('imported', 0) / len(leads), 1) if leads else 0.0,
                'avg_per_day': round(
                    (sum(day_values) / len(day_values)) if day_values else 0.0,
                    1,
                ),
                'spend_total': round(sum(spend_values), 2) if spend_values else 0.0,
                'top_source': (
                    max(
                        (
                            ('Instagram', by_source.get('instagram', 0)),
                            ('Facebook', by_source.get('facebook', 0)),
                            ('Meta', by_source.get('meta', 0)),
                        ),
                        key=lambda x: x[1],
                    )[0]
                    if leads else '—'
                ),
                'video_creatives': by_creative.get('video', 0),
                'image_creatives': by_creative.get('image', 0),
                'creative_assets': len(creative_rows),
                'campaigns_with_leads': len([r for r in campaign_rows if r['leads']]),
            },
        }

    @api.model
    def _safe_sync(self, label, func):
        """Run a sync step without aborting the whole hub sync."""
        try:
            return True, func(), ''
        except Exception as exc:
            return False, None, '%s: %s' % (label, exc)

    @api.model
    def action_full_sync(self, selected_ad_account_id=None, date_from=None, date_to=None):
        """Lean Meta sync for the hub (avoids browser/proxy timeouts).

        Skips the full campaign tree (use Kampanyaları Çek). Includes inbox + leads.
        """
        parts = []
        warnings = []

        ok, synced, err = self._safe_sync(
            'Profil',
            lambda: self.env['tcrm.marketing.profile']._sync_profiles_only(),
        )
        if ok:
            parts.append(_('%s profil') % len(synced or []))
        elif err:
            warnings.append(err)

        for label, model_name in (
            ('Hesaplar', 'tcrm.marketing.account'),
            ('Reklam hesapları', 'tcrm.marketing.ad.account'),
            ('Gönderiler', 'tcrm.marketing.post'),
        ):
            ok, _res, err = self._safe_sync(
                label,
                lambda m=model_name: self.env[m].action_sync_from_zernio(),
            )
            if not ok and err:
                warnings.append(err)

        ok, _res, err = self._safe_sync(
            'Gelen kutusu',
            lambda: self.env['tcrm.marketing.conversation'].action_sync_from_zernio(),
        )
        if ok:
            parts.append(_('gelen kutusu'))
        elif err:
            warnings.append(err)

        ok, _res, err = self._safe_sync(
            'Lead formları',
            lambda: self.env['tcrm.marketing.lead.form'].action_sync_from_zernio(),
        )
        if ok:
            try:
                total = self.env['tcrm.marketing.meta.lead'].action_sync_all_forms(
                    import_crm=True,
                    max_pages_per_form=2,
                )
                parts.append(_('%s lead') % total)
            except Exception as exc:
                warnings.append(_('Lead: %s') % exc)
        elif err:
            warnings.append(err)

        camp_count = self.env['tcrm.marketing.campaign'].search_count([
            ('company_id', '=', self.env.company.id),
        ])
        parts.append(_('%s kampanya (önbellek)') % camp_count)

        data = self.get_dashboard(
            selected_ad_account_id=selected_ad_account_id,
            date_from=date_from,
            date_to=date_to,
        )
        msg = _('Senkron tamam: %s.') % (', '.join(parts) if parts else _('kısmi'))
        if warnings:
            msg = '%s (%s)' % (msg, '; '.join(warnings[:2]))
        data['sync_message'] = msg
        return data

    @api.model
    def action_sync_inbox_only(self, selected_ad_account_id=None, date_from=None, date_to=None):
        self.env['tcrm.marketing.conversation'].action_sync_from_zernio()
        try:
            self.env['tcrm.marketing.comment'].action_sync_from_zernio()
        except Exception:
            pass
        data = self.get_dashboard(
            selected_ad_account_id=selected_ad_account_id,
            date_from=date_from,
            date_to=date_to,
        )
        data['sync_message'] = _(
            '%s konuşma gelen kutusunda.'
        ) % data['stats']['conversations']
        return data

    @api.model
    def action_sync_campaigns_only(self, selected_ad_account_id=None, date_from=None, date_to=None):
        self.env['tcrm.marketing.campaign'].action_sync_from_zernio()
        data = self.get_dashboard(
            selected_ad_account_id=selected_ad_account_id,
            date_from=date_from,
            date_to=date_to,
        )
        data['sync_message'] = _(
            '%s kampanya TCRM’de. Seçili reklam hesabına göre listelenir.'
        ) % data['stats']['campaigns']
        return data

    @api.model
    def action_sync_google_ads(self, selected_ad_account_id=None):
        """Sync Google Ads connection: accounts → customers → campaigns → keywords."""
        Account = self.env['tcrm.marketing.account']
        AdAccount = self.env['tcrm.marketing.ad.account']
        Campaign = self.env['tcrm.marketing.campaign']
        Keyword = self.env['tcrm.marketing.google.keyword']

        # Pull googleads social + customer accounts
        Account.action_sync_from_zernio()
        AdAccount.action_sync_from_zernio()

        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
        except ZernioError as exc:
            raise UserError(str(exc)) from exc

        google_socials = Account.search([
            ('platform', '=', 'googleads'),
            ('active', '=', True),
            ('company_id', '=', self.env.company.id),
        ])
        synced_camps = 0
        for social in google_socials:
            ad_accs = AdAccount.search([
                ('account_id', '=', social.id),
                ('active', '=', True),
            ])
            if not ad_accs:
                # Tree can still work with accountId alone — create placeholder after list
                try:
                    rows = client.list_ad_accounts(social.zernio_id)
                except ZernioError:
                    rows = []
                for item in rows:
                    act_id = str(item.get('id') or '')
                    if not act_id:
                        continue
                    AdAccount.sudo().create({
                        'name': item.get('name') or act_id,
                        'meta_act_id': act_id,
                        'provider': 'google',
                        'currency': item.get('currency') or False,
                        'account_status': str(item.get('accountStatus') or '') or False,
                        'account_id': social.id,
                        'last_sync_at': fields.Datetime.now(),
                        'active': True,
                    })
                ad_accs = AdAccount.search([('account_id', '=', social.id), ('active', '=', True)])

            for ad_acc in ad_accs:
                page = 1
                while page <= 40:
                    try:
                        tree = client.get_ads_tree(
                            page=page,
                            limit=50,
                            source='all',
                            account_id=social.zernio_id,
                            ad_account_id=ad_acc.meta_act_id,
                            date_from='2020-01-01',
                            date_to=fields.Date.today().isoformat(),
                        )
                    except ZernioError as exc:
                        raise UserError(str(exc)) from exc
                    for item in (tree.get('campaigns') or []):
                        Campaign._upsert_campaign_from_tree(
                            item,
                            ad_account=ad_acc,
                            social_account=social,
                        )
                        synced_camps += 1
                    pagination = tree.get('pagination') or {}
                    total_pages = int(pagination.get('pages') or 1)
                    if page >= total_pages or not (tree.get('campaigns') or []):
                        break
                    page += 1

        Keyword.action_sync_from_zernio()
        data = self.get_google_ads_dashboard(selected_ad_account_id=selected_ad_account_id)
        data['sync_message'] = _(
            'Google Ads senkronize edildi: %(camps)s kampanya, %(kw)s anahtar kelime.'
        ) % {
            'camps': data['stats']['campaigns'],
            'kw': data['stats']['keywords'],
        }
        return data

    @api.model
    def get_google_ads_dashboard(self, selected_ad_account_id=None, fetch_insights=True):
        """Payload for the Google Ads hub section."""
        company = self.env.company
        ICP = self.env['ir.config_parameter'].sudo()
        param_key = f'tcrm_marketing_hub.selected_google_ad_account.{company.id}'
        if selected_ad_account_id:
            ICP.set_param(param_key, str(selected_ad_account_id))
        else:
            raw = ICP.get_param(param_key)
            selected_ad_account_id = int(raw) if raw and str(raw).isdigit() else False

        socials = self.env['tcrm.marketing.account'].search([
            ('company_id', '=', company.id),
            ('platform', '=', 'googleads'),
            ('active', '=', True),
        ])
        ad_accounts = self.env['tcrm.marketing.ad.account'].search([
            ('company_id', '=', company.id),
            ('provider', '=', 'google'),
            ('active', '=', True),
        ])
        selected = ad_accounts.filtered(lambda a: a.id == selected_ad_account_id)[:1]
        if not selected and ad_accounts:
            selected = ad_accounts[:1]
            selected_ad_account_id = selected.id

        camp_domain = [
            ('company_id', '=', company.id),
            ('platform', '=', 'google'),
        ]
        if selected:
            camp_domain.append(('ad_account_id', '=', selected.id))
        campaigns = self.env['tcrm.marketing.campaign'].search(camp_domain, limit=200)

        kw_domain = [('company_id', '=', company.id)]
        if selected:
            kw_domain.append(('ad_account_id', '=', selected.id))
        keywords = self.env['tcrm.marketing.google.keyword'].search(kw_domain, limit=300)

        ads_domain = [
            ('company_id', '=', company.id),
            ('source_platform', '=', 'google'),
        ]
        if selected:
            ads_domain.append(('ad_account_id', '=', selected.id))
        ads = self.env['tcrm.marketing.meta.ad'].search(ads_domain, limit=200)

        insights = []
        insights_error = ''
        if fetch_insights and selected and selected.account_id:
            try:
                from .marketing_google import DEFAULT_GAQL_CAMPAIGNS
                client = self.env['tcrm.marketing.profile']._get_zernio_client()
                raw = client.query_ad_insights(
                    account_id=selected.account_id.zernio_id,
                    query=DEFAULT_GAQL_CAMPAIGNS,
                    customer_id=selected.meta_act_id,
                )
                for row in (raw.get('data') or []):
                    camp = row.get('campaign') or {}
                    metrics = row.get('metrics') or {}
                    cost_micros = float(metrics.get('costMicros') or metrics.get('cost_micros') or 0)
                    insights.append({
                        'campaign_id': str(camp.get('id') or ''),
                        'name': camp.get('name') or '',
                        'status': camp.get('status') or '',
                        'channel': camp.get('advertisingChannelType') or camp.get('advertising_channel_type') or '',
                        'impressions': int(float(metrics.get('impressions') or 0)),
                        'clicks': int(float(metrics.get('clicks') or 0)),
                        'cost': round(cost_micros / 1_000_000.0, 2),
                        'conversions': float(metrics.get('conversions') or 0),
                        'ctr': float(metrics.get('ctr') or 0),
                        'avg_cpc': round(float(metrics.get('averageCpc') or metrics.get('average_cpc') or 0) / 1_000_000.0, 2)
                        if float(metrics.get('averageCpc') or metrics.get('average_cpc') or 0) > 1000
                        else float(metrics.get('averageCpc') or metrics.get('average_cpc') or 0),
                    })
            except Exception as exc:
                insights_error = str(exc)
                _logger = __import__('logging').getLogger(__name__)
                _logger.warning('Google insights failed: %s', exc)

        total_spend = sum(c.spend or 0 for c in campaigns)
        total_clicks = sum(c.clicks or 0 for c in campaigns)
        total_impr = sum(c.impressions or 0 for c in campaigns)

        def _fmt_kw(k):
            return {
                'id': k.id,
                'keyword': k.keyword,
                'match_type': k.match_type,
                'status': k.status,
                'negative': k.negative,
                'campaign_name': k.campaign_name or '',
                'campaign_status': k.campaign_status or '',
                'adset_name': k.adset_name or '',
                'adset_status': k.adset_status or '',
            }

        def _fmt_ad(ad):
            creative = {}
            try:
                creative = __import__('json').loads(ad.creative_json or '{}')
            except Exception:
                creative = {}
            headlines = creative.get('googleHeadlines') or []
            if creative.get('googleHeadline') and creative.get('googleHeadline') not in headlines:
                headlines = [creative.get('googleHeadline')] + list(headlines)
            descriptions = creative.get('googleDescriptions') or []
            if creative.get('googleDescription') and creative.get('googleDescription') not in descriptions:
                descriptions = [creative.get('googleDescription')] + list(descriptions)
            return {
                'id': ad.id,
                'name': ad.name,
                'status': ad.status or '',
                'campaign': ad.campaign_id.name if ad.campaign_id else '',
                'adset': ad.adset_name or '',
                'spend': ad.spend or 0,
                'impressions': ad.impressions or 0,
                'clicks': ad.clicks or 0,
                'headlines': headlines[:8],
                'descriptions': descriptions[:4],
                'media_type': ad.creative_media_type or 'none',
                'thumbnail_url': ad.creative_thumbnail_url or ad.creative_image_url or '',
                'image_url': ad.creative_image_url or '',
                'video_url': ad.creative_video_url or '',
            }

        return {
            'selected_ad_account_id': selected_ad_account_id or False,
            'stats': {
                'connections': len(socials),
                'ad_accounts': len(ad_accounts),
                'campaigns': len(campaigns),
                'keywords': len(keywords),
                'ads': len(ads),
                'spend': total_spend,
                'clicks': total_clicks,
                'impressions': total_impr,
                'active_campaigns': len(campaigns.filtered(lambda c: c.status == 'active')),
                'paused_campaigns': len(campaigns.filtered(lambda c: c.status == 'paused')),
            },
            'connections': [{
                'id': a.id,
                'name': a.name,
                'username': a.username or '',
                'status': a.status,
                'zernio_id': a.zernio_id,
                'last_sync_at': fields.Datetime.to_string(a.last_sync_at) if a.last_sync_at else '',
            } for a in socials],
            'ad_accounts': [{
                'id': a.id,
                'name': a.name,
                'customer_id': a.meta_act_id,
                'currency': a.currency or '',
                'account_status': a.account_status or '',
                'campaign_count': a.campaign_count,
                'last_sync_at': fields.Datetime.to_string(a.last_sync_at) if a.last_sync_at else '',
                'google_ads_url': f'https://ads.google.com/aw/overview?ocid={a.meta_act_id}',
            } for a in ad_accounts],
            'campaigns': [self._serialize_campaign_row(c) for c in campaigns],
            'keywords': [_fmt_kw(k) for k in keywords],
            'ads': [_fmt_ad(ad) for ad in ads],
            'insights': insights,
            'insights_error': insights_error,
            'features': [
                {'id': 'campaigns', 'label': 'Kampanyalar', 'desc': 'Search, Display, Performance Max keşfi (/ads/tree)'},
                {'id': 'keywords', 'label': 'Anahtar Kelimeler', 'desc': 'Search kelime kriterleri (/ads/keywords)'},
                {'id': 'insights', 'label': 'GAQL Performans', 'desc': 'Ham Google Ads sorgusu (/ads/insights)'},
                {'id': 'rsa', 'label': 'RSA Kreatifler', 'desc': 'Başlık / açıklama önizleme'},
                {'id': 'settings', 'label': 'Hesap Ayarları', 'desc': 'Müşteri ID, para birimi, bağlantı durumu'},
            ],
        }

    @api.model
    def get_creatives_gallery(self, provider=None, limit=120):
        """Unified Meta + Google creative gallery for the hub."""
        company = self.env.company
        Creative = self.env['tcrm.marketing.creative'].sudo()
        MetaAd = self.env['tcrm.marketing.meta.ad'].sudo()
        domain = [('company_id', '=', company.id)]
        if provider in ('meta', 'google'):
            domain.append(('provider', '=', provider))
        library = Creative.search(domain, limit=limit, order='write_date desc')

        ad_domain = [
            ('company_id', '=', company.id),
            '|', '|',
            ('creative_image_url', '!=', False),
            ('creative_thumbnail_url', '!=', False),
            ('creative_video_url', '!=', False),
        ]
        if provider == 'google':
            ad_domain.append(('source_platform', '=', 'google'))
        elif provider == 'meta':
            ad_domain.append(('source_platform', 'in', ('meta', 'facebook', 'instagram')))
        ads = MetaAd.search(ad_domain, limit=limit, order='write_date desc')

        def _lib_row(c):
            return {
                'id': f'lib-{c.id}',
                'source': 'library',
                'provider': c.provider,
                'name': c.name,
                'media_type': c.media_type,
                'image_url': c.image_url or '',
                'thumbnail_url': c.thumbnail_url or c.image_url or '',
                'video_url': c.video_url or '',
                'video_id': c.video_id or '',
                'permalink': c.permalink or '',
                'campaign_name': c.campaign_name or '',
                'body': (c.body or '')[:200],
            }

        def _ad_row(ad):
            return {
                'id': f'ad-{ad.id}',
                'source': 'ad',
                'provider': 'google' if ad.source_platform == 'google' else 'meta',
                'name': ad.name,
                'media_type': ad.creative_media_type or 'none',
                'image_url': ad.creative_image_url or '',
                'thumbnail_url': ad.creative_thumbnail_url or ad.creative_image_url or '',
                'video_url': ad.creative_video_url or '',
                'video_id': '',
                'permalink': ad.creative_permalink or '',
                'campaign_name': ad.campaign_id.name if ad.campaign_id else '',
                'body': (ad.creative_body or '')[:200],
                'title': ad.creative_title or '',
                'ad_id': ad.id,
            }

        items = [_lib_row(c) for c in library] + [_ad_row(a) for a in ads]
        # Dedupe by thumbnail/image url
        seen = set()
        unique = []
        for it in items:
            key = it.get('thumbnail_url') or it.get('image_url') or it.get('video_url') or it['id']
            if key in seen:
                continue
            seen.add(key)
            unique.append(it)

        return {
            'stats': {
                'library': len(library),
                'ads_with_media': len(ads),
                'images': sum(1 for i in unique if i['media_type'] == 'image'),
                'videos': sum(1 for i in unique if i['media_type'] == 'video'),
                'total': len(unique),
            },
            'items': unique[:limit],
        }

    @api.model
    def action_sync_creatives(self, selected_ad_account_id=None, date_from=None, date_to=None):
        """Full creative backfill: campaigns (metaads) + libraries + Google assets + ad refresh."""
        # Prefer dedicated ads connections when syncing campaigns
        self.env['tcrm.marketing.account'].action_sync_from_zernio()
        self.env['tcrm.marketing.ad.account'].action_sync_from_zernio()
        try:
            self.env['tcrm.marketing.campaign'].action_sync_from_zernio()
        except Exception as exc:
            _logger = __import__('logging').getLogger(__name__)
            _logger.warning('Campaign sync during creatives: %s', exc)
        counts = self.env['tcrm.marketing.creative'].action_sync_all_creatives()
        gallery = self.get_creatives_gallery()
        gallery['sync_message'] = _(
            'Kreatifler güncellendi — kütüphane Meta:%(meta)s Google:%(google)s, reklam yenileme:%(ads)s, galeri:%(total)s'
        ) % {
            'meta': counts.get('meta_library', 0),
            'google': counts.get('google_assets', 0),
            'ads': counts.get('ads_refreshed', 0),
            'total': gallery['stats']['total'],
        }
        # Keep dashboard filters working for callers that expect full dashboard keys
        try:
            dash = self.get_dashboard(
                selected_ad_account_id=selected_ad_account_id,
                date_from=date_from,
                date_to=date_to,
            )
            dash['creatives'] = gallery
            dash['sync_message'] = gallery['sync_message']
            return dash
        except Exception:
            return gallery

    @api.model
    def action_sync_leads_only(self, selected_ad_account_id=None, date_from=None, date_to=None):
        Form = self.env['tcrm.marketing.lead.form']
        Form.action_sync_from_zernio()
        total = self.env['tcrm.marketing.meta.lead'].action_sync_all_forms(
            import_crm=True,
            max_pages_per_form=8,
        )
        try:
            self.env['tcrm.marketing.meta.lead'].action_refresh_sources()
        except Exception:
            pass
        data = self.get_dashboard(
            selected_ad_account_id=selected_ad_account_id,
            date_from=date_from,
            date_to=date_to,
        )
        data['sync_message'] = _(
            '%s lead senkronize edildi; Instagram / Facebook kaynakları güncellendi.'
        ) % total
        return data

    @api.model
    def action_import_pending_leads(self, selected_ad_account_id=None, date_from=None, date_to=None):
        pending = self.env['tcrm.marketing.meta.lead'].search([
            ('crm_lead_id', '=', False),
            ('company_id', '=', self.env.company.id),
        ], limit=200)
        pending.action_import_to_crm()
        data = self.get_dashboard(
            selected_ad_account_id=selected_ad_account_id,
            date_from=date_from,
            date_to=date_to,
        )
        data['sync_message'] = _('%s bekleyen lead CRM’e aktarıldı.') % len(pending)
        return data

    # ------------------------------------------------------------------
    # Page selection / connection management (tenant-scoped)
    # ------------------------------------------------------------------

    @api.model
    def _check_page_manager(self):
        if not self.env.user.has_group('tcrm_marketing_hub.group_marketing_manager'):
            raise AccessError(_(
                'Sayfa seçimini değiştirmek için Marketing Yönetici yetkisi gerekir.'
            ))

    @api.model
    def _company_accounts(self, *, active_only=False):
        domain = [('company_id', '=', self.env.company.id)]
        if active_only:
            domain.append(('active', '=', True))
        return self.env['tcrm.marketing.account'].search(domain)

    @api.model
    def get_page_management(self):
        """Profile + pages for hub page-selection UI (no API keys/tokens)."""
        company = self.env.company
        Profile = self.env['tcrm.marketing.profile']
        profiles = Profile.search([
            ('company_id', '=', company.id),
            ('active', '=', True),
        ], order='is_default desc, id')
        default = profiles.filtered('is_default')[:1] or profiles[:1]
        accounts = self._company_accounts()
        can_manage = self.env.user.has_group('tcrm_marketing_hub.group_marketing_manager')
        return {
            'profile': {
                'id': default.id,
                'name': default.name,
                'zernio_id': default.zernio_id,
            } if default else None,
            'profiles': [{
                'id': p.id,
                'name': p.name,
                'zernio_id': p.zernio_id,
                'is_default': p.is_default,
                'last_sync_at': fields.Datetime.to_string(p.last_sync_at) if p.last_sync_at else '',
            } for p in profiles],
            'accounts': [{
                'id': a.id,
                'name': a.name,
                'display_name': a.display_name,
                'platform': a.platform,
                'username': a.username or '',
                'status': a.status,
                'active': a.active,
                'sync_enabled': a.sync_enabled,
                'sync_error': a.sync_error or '',
                'last_sync_at': fields.Datetime.to_string(a.last_sync_at) if a.last_sync_at else '',
                'disabled_at': fields.Datetime.to_string(a.disabled_at) if a.disabled_at else '',
                'zernio_id': a.zernio_id,
                'profile_name': a.profile_id.name if a.profile_id else '',
                'followers': a.follower_count,
            } for a in accounts],
            'can_manage': can_manage,
            'company_id': company.id,
            'company_name': company.name,
        }

    @api.model
    def set_page_selection(self, account_ids_enabled):
        """Enable sync for given account IDs; disable others in this company."""
        self._check_page_manager()
        company = self.env.company
        enabled_ids = {int(i) for i in (account_ids_enabled or []) if i}
        accounts = self._company_accounts()
        for account in accounts:
            want = account.id in enabled_ids
            if account.sync_enabled != want:
                account.write({'sync_enabled': want})
        return self.get_page_management()

    @api.model
    def action_refresh_pages(self):
        """Sync social accounts from Zernio for the current company."""
        self._check_page_manager()
        self.env['tcrm.marketing.account'].action_sync_from_zernio()
        data = self.get_page_management()
        data['message'] = _('Sayfalar Zernio’dan yenilendi.')
        return data

    @api.model
    def action_test_connection(self):
        """Test Zernio connectivity via list_profiles. Never returns tokens."""
        self._check_page_manager()
        try:
            client = self.env['tcrm.marketing.profile']._get_zernio_client()
            profiles = client.list_profiles() or []
        except (ZernioError, UserError) as exc:
            err = str(exc)
            for needle in ('api_key', 'apikey', 'token', 'bearer', 'authorization'):
                if needle in err.lower():
                    err = _('Bağlantı hatası (ayrıntılar gizlendi).')
                    break
            return {
                'success': False,
                'message': err,
                'profile_count': 0,
            }
        safe_names = []
        for item in profiles[:20]:
            if isinstance(item, dict):
                name = item.get('name') or item.get('_id') or item.get('id')
                if name:
                    safe_names.append(str(name))
        return {
            'success': True,
            'message': _('%s Zernio profili erişilebilir.') % len(profiles),
            'profile_count': len(profiles),
            'profile_names': safe_names,
        }

    @api.model
    def action_disable_page(self, account_id):
        self._check_page_manager()
        account = self.env['tcrm.marketing.account'].browse(int(account_id)).exists()
        if not account or account.company_id != self.env.company:
            raise UserError(_('Sayfa bulunamadı veya bu şirkete ait değil.'))
        account.write({'sync_enabled': False})
        return self.get_page_management()

    @api.model
    def action_enable_page(self, account_id):
        self._check_page_manager()
        account = self.env['tcrm.marketing.account'].browse(int(account_id)).exists()
        if not account or account.company_id != self.env.company:
            raise UserError(_('Sayfa bulunamadı veya bu şirkete ait değil.'))
        account.write({'sync_enabled': True, 'sync_error': False})
        return self.get_page_management()


def json_loads_safe(text):
    import json
    if not text:
        return {}
    if isinstance(text, dict):
        return text
    return json.loads(text)
