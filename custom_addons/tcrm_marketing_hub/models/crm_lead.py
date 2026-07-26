# -*- coding: utf-8 -*-
import re

from tcrm import api, fields, models

from .marketing_meta_lead import SOURCE_LABELS


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    marketing_meta_lead_ids = fields.One2many(
        'tcrm.marketing.meta.lead',
        'crm_lead_id',
        string='Marketing Hub Leadleri',
    )
    marketing_has_meta_lead = fields.Boolean(
        string='Marketing Kaynağı Var',
        compute='_compute_marketing_source_fields',
    )
    mh_source_platform = fields.Char(
        string='Lead Kaynağı / Platform',
        compute='_compute_marketing_source_fields',
    )
    mh_campaign_name = fields.Char(
        string='Kampanya Adı',
        compute='_compute_marketing_source_fields',
    )
    mh_campaign_id_remote = fields.Char(
        string='Meta Kampanya ID',
        compute='_compute_marketing_source_fields',
    )
    mh_ad_name = fields.Char(
        string='Reklam Adı',
        compute='_compute_marketing_source_fields',
    )
    mh_ad_id = fields.Char(
        string='Meta Ad ID',
        compute='_compute_marketing_source_fields',
    )
    mh_form_name = fields.Char(
        string='Form Adı',
        compute='_compute_marketing_source_fields',
    )
    mh_form_zernio_id = fields.Char(
        string='Meta Form ID',
        compute='_compute_marketing_source_fields',
    )
    mh_page_name = fields.Char(
        string='Bağlı Sayfa',
        compute='_compute_marketing_source_fields',
    )
    mh_page_zernio_id = fields.Char(
        string='Sayfa Zernio ID',
        compute='_compute_marketing_source_fields',
    )
    mh_profile_name = fields.Char(
        string='Profil Adı',
        compute='_compute_marketing_source_fields',
    )
    mh_created_time = fields.Datetime(
        string='Orijinal Gönderim',
        compute='_compute_marketing_source_fields',
    )
    mh_last_sync_at = fields.Datetime(
        string='Son Senkron',
        compute='_compute_marketing_source_fields',
    )
    mh_leadgen_id = fields.Char(
        string='Harici Lead ID',
        compute='_compute_marketing_source_fields',
    )
    mh_sync_state = fields.Char(
        string='Senkron Durumu',
        compute='_compute_marketing_source_fields',
    )
    mh_creative_media_type = fields.Char(
        string='Kreatif Tipi',
        compute='_compute_marketing_source_fields',
    )
    mh_creative_image_url = fields.Char(
        string='Kreatif Görsel URL',
        compute='_compute_marketing_source_fields',
    )
    mh_creative_video_url = fields.Char(
        string='Kreatif Video URL',
        compute='_compute_marketing_source_fields',
    )
    mh_creative_thumbnail_url = fields.Char(
        string='Kreatif Önizleme URL',
        compute='_compute_marketing_source_fields',
    )
    mh_creative_body = fields.Text(
        string='Kreatif Metin',
        compute='_compute_marketing_source_fields',
    )
    mh_creative_permalink = fields.Char(
        string='Kreatif Bağlantı',
        compute='_compute_marketing_source_fields',
    )
    mh_creative_html = fields.Html(
        string='Kreatif Önizleme',
        compute='_compute_marketing_source_fields',
        sanitize=False,
    )

    def _get_primary_marketing_meta_lead(self):
        """Resolve linked meta lead with sudo (CRM users may lack marketing ACL)."""
        self.ensure_one()
        MetaLead = self.env['tcrm.marketing.meta.lead'].sudo()
        if self.marketing_meta_lead_ids:
            return self.marketing_meta_lead_ids[:1].sudo()
        return MetaLead.search([('crm_lead_id', '=', self.id)], limit=1)

    @api.depends(
        'marketing_meta_lead_ids',
        'marketing_meta_lead_ids.source_platform',
        'marketing_meta_lead_ids.campaign_name',
        'marketing_meta_lead_ids.campaign_id_remote',
        'marketing_meta_lead_ids.ad_name',
        'marketing_meta_lead_ids.ad_id',
        'marketing_meta_lead_ids.form_id',
        'marketing_meta_lead_ids.account_id',
        'marketing_meta_lead_ids.created_time',
        'marketing_meta_lead_ids.leadgen_id',
        'marketing_meta_lead_ids.state',
        'marketing_meta_lead_ids.creative_html',
    )
    def _compute_marketing_source_fields(self):
        state_labels = dict(
            self.env['tcrm.marketing.meta.lead']._fields['state'].selection
        )
        for lead in self:
            meta = lead._get_primary_marketing_meta_lead()
            if not meta:
                lead.marketing_has_meta_lead = False
                lead.mh_source_platform = False
                lead.mh_campaign_name = False
                lead.mh_campaign_id_remote = False
                lead.mh_ad_name = False
                lead.mh_ad_id = False
                lead.mh_form_name = False
                lead.mh_form_zernio_id = False
                lead.mh_page_name = False
                lead.mh_page_zernio_id = False
                lead.mh_profile_name = False
                lead.mh_created_time = False
                lead.mh_last_sync_at = False
                lead.mh_leadgen_id = False
                lead.mh_sync_state = False
                lead.mh_creative_media_type = False
                lead.mh_creative_image_url = False
                lead.mh_creative_video_url = False
                lead.mh_creative_thumbnail_url = False
                lead.mh_creative_body = False
                lead.mh_creative_permalink = False
                lead.mh_creative_html = False
                continue

            account = meta.account_id
            form = meta.form_id
            last_sync = form.last_sync_at or (account.last_sync_at if account else False)
            platform_key = meta.source_platform or ''
            lead.marketing_has_meta_lead = True
            lead.mh_source_platform = SOURCE_LABELS.get(platform_key, platform_key) or False
            lead.mh_campaign_name = meta.campaign_name or False
            lead.mh_campaign_id_remote = meta.campaign_id_remote or False
            lead.mh_ad_name = meta.ad_name or False
            lead.mh_ad_id = meta.ad_id or False
            lead.mh_form_name = form.name if form else False
            lead.mh_form_zernio_id = form.zernio_form_id if form else False
            lead.mh_page_name = account.display_name if account else False
            lead.mh_page_zernio_id = account.zernio_id if account else False
            lead.mh_profile_name = (
                account.profile_id.name if account and account.profile_id else False
            )
            lead.mh_created_time = meta.created_time or False
            lead.mh_last_sync_at = last_sync or False
            lead.mh_leadgen_id = meta.leadgen_id or False
            lead.mh_sync_state = state_labels.get(meta.state, meta.state) or False
            lead.mh_creative_media_type = meta.creative_media_type or False
            lead.mh_creative_image_url = meta.creative_image_url or False
            lead.mh_creative_video_url = meta.creative_video_url or False
            lead.mh_creative_thumbnail_url = meta.creative_thumbnail_url or False
            lead.mh_creative_body = meta.creative_body or False
            lead.mh_creative_permalink = meta.creative_permalink or False
            lead.mh_creative_html = meta.creative_html or False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-opportunity for every new CRM record
            vals.setdefault('type', 'opportunity')
            # Never keep platform prefixes in the title
            if vals.get('name'):
                vals['name'] = re.sub(
                    r'^\s*\[(?:Instagram|Facebook|Meta|IG|FB)\]\s*',
                    '',
                    vals['name'],
                    flags=re.IGNORECASE,
                ).strip() or vals['name']
            # Leave expected revenue empty for the user to fill
            if 'expected_revenue' not in vals:
                vals['expected_revenue'] = 0.0
        return super().create(vals_list)
