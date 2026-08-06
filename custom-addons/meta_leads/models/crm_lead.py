# -*- coding: utf-8 -*-
try:
    from tcrm import models, fields, api
except ImportError:
    from odoo import models, fields, api
import os
import requests
import logging
import time

_logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Stage-name patterns that trigger CAPI events.
# Matching is case-insensitive and checks if any keyword is contained
# in the stage name.  Covers Turkish + English naming conventions.
# -----------------------------------------------------------------------
QUALIFIED_STAGE_KEYWORDS = [
    "qualified", "nitelikli", "niteliklendirme",
    "proposition", "teklif",
]

WON_STAGE_KEYWORDS = [
    "won", "sold", "satisfied", "kazanıldı", "kazanildi",
    "satıldı", "satildi", "satış", "satis",
    "memnun", "başarılı", "basarili",
    "closed won", "kapalı kazanıldı",
]


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # ===================================================================
    # Basic Meta fields
    # ===================================================================
    meta_leadgen_id = fields.Char(string='Meta Leadgen ID', index=True)
    meta_page_id = fields.Char(string='Meta Page ID', index=True)
    meta_form_id = fields.Char(string='Meta Form ID', index=True)
    meta_raw_payload = fields.Text(string='Meta Raw Payload')
    meta_submitted_on = fields.Datetime(
        string='Submitted On',
        help='When the lead form was submitted on Meta/Facebook',
    )

    # Campaign tracking fields
    meta_campaign_id = fields.Char(string='Meta Campaign ID', index=True)
    meta_campaign_name = fields.Char(string='Meta Campaign Name')
    meta_adset_id = fields.Char(string='Meta Ad Set ID', index=True)
    meta_adset_name = fields.Char(string='Meta Ad Set Name')
    meta_ad_id = fields.Char(string='Meta Ad ID', index=True)
    meta_ad_name = fields.Char(string='Meta Ad Name')
    meta_medium = fields.Char(string='Medium', default='facebook_ads')
    meta_source = fields.Char(string='Source', default='facebook')
    meta_platform = fields.Char(string='Platform', help='Instagram or Facebook')

    # Form data
    meta_form_answers = fields.Text(
        string='Form Answers',
        help="Client's complete form responses",
    )

    # Ad Creative fields
    meta_creative_id = fields.Char(string='Creative ID', index=True)
    meta_creative_type = fields.Selection([
        ('image', 'Image'),
        ('video', 'Video'),
        ('carousel', 'Carousel'),
        ('collection', 'Collection'),
    ], string='Creative Type')
    meta_creative_media_url = fields.Char(
        string='Creative Media URL',
        help='Direct URL to creative image or video thumbnail',
    )
    meta_creative_body = fields.Text(string='Ad Body Text')
    meta_creative_title = fields.Char(string='Ad Title')
    meta_creative_cta = fields.Char(string='Call to Action')
    meta_creative_preview = fields.Html(
        string='Creative Preview',
        help='Formatted preview of the ad creative',
        compute='_compute_creative_preview',
        store=True,
    )

    # Legacy field for compatibility
    meta_ad_creative = fields.Html(
        string='Ad Creative Preview (Legacy)',
        help='Visual preview of the ad creative content',
    )

    # ===================================================================
    # Meta CAPI tracking fields
    # ===================================================================
    meta_capi_lead_event_sent = fields.Boolean(
        string='Lead Event Sent',
        default=False,
        help='Whether a Lead conversion event was sent to Meta CAPI',
    )
    meta_capi_purchase_event_sent = fields.Boolean(
        string='Purchase Event Sent',
        default=False,
        help='Whether a Purchase conversion event was sent to Meta CAPI',
    )
    meta_capi_last_event = fields.Char(
        string='Last CAPI Event',
        readonly=True,
        help='Name of the last Meta CAPI event sent for this lead',
    )
    meta_capi_last_event_time = fields.Datetime(
        string='Last CAPI Event Time',
        readonly=True,
        help='When the last Meta CAPI event was sent',
    )
    meta_capi_event_log = fields.Text(
        string='CAPI Event Log',
        readonly=True,
        help='Log of all Meta CAPI events sent for this lead',
    )

    # Website tracking fields (captured from form submissions)
    meta_fbc = fields.Char(
        string='Click ID (fbc)',
        help='Facebook click ID cookie — captured from website form',
    )
    meta_fbp = fields.Char(
        string='Browser ID (fbp)',
        help='Facebook browser ID cookie — captured from website form',
    )
    meta_client_ip = fields.Char(
        string='Client IP',
        help='Client IP address from form submission (not hashed)',
    )
    meta_client_user_agent = fields.Char(
        string='Client User Agent',
        help='Client browser user-agent from form submission (not hashed)',
    )
    meta_subscription_id = fields.Char(
        string='Subscription ID',
        help='Meta Subscription ID — not hashed',
    )
    meta_event_source_url = fields.Char(
        string='Event Source URL',
        help='URL where the lead form was submitted (e.g. https://akod.tech/...)',
    )
    meta_event_id = fields.Char(
        string='Browser Event ID',
        index=True,
        help='Shared event_id for Pixel ↔ Conversions API deduplication',
    )
    meta_date_of_birth = fields.Date(
        string='Date of Birth (CAPI)',
        help='Optional DOB for Meta Event Match Quality — real values only',
    )
    meta_gender = fields.Selection(
        [('m', 'Male'), ('f', 'Female')],
        string='Gender (CAPI)',
        help='Optional gender for Meta Event Match Quality — real values only',
    )

    # ===================================================================
    # Creative preview compute
    # ===================================================================
    @api.depends(
        'meta_creative_media_url', 'meta_creative_body',
        'meta_creative_title', 'meta_creative_cta',
        'meta_ad_name', 'meta_creative_type',
    )
    def _compute_creative_preview(self):
        """Compute formatted creative preview"""
        for lead in self:
            if not any([lead.meta_creative_media_url, lead.meta_creative_body, lead.meta_ad_name]):
                lead.meta_creative_preview = False
                continue

            html_parts = []

            # Header
            html_parts.append('''
            <div style="border: 1px solid #dee2e6; border-radius: 8px; padding: 16px; margin: 8px 0; background: #fff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            ''')

            # Ad name
            if lead.meta_ad_name:
                html_parts.append(f'''
                <div style="background: #f8f9fa; padding: 12px; border-radius: 6px; margin-bottom: 12px; border-left: 3px solid #007bff;">
                    <strong style="color: #007bff;">📱 {lead.meta_ad_name}</strong>
                </div>
                ''')

            # Media preview
            if lead.meta_creative_media_url:
                media_type = lead.meta_creative_type or 'image'
                if media_type == 'video':
                    html_parts.append(f'''
                    <div style="text-align: center; margin-bottom: 12px;">
                        <div style="position: relative; display: inline-block;">
                            <img src="{lead.meta_creative_media_url}" style="max-width: 300px; max-height: 200px; border-radius: 6px; border: 1px solid #ddd;" alt="Video Thumbnail"/>
                            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.7); border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center;">
                                <span style="color: white; font-size: 16px;">▶️</span>
                            </div>
                        </div>
                        <div style="font-size: 12px; color: #6c757d; margin-top: 4px;">🎬 Video Creative</div>
                    </div>
                    ''')
                else:
                    html_parts.append(f'''
                    <div style="text-align: center; margin-bottom: 12px;">
                        <img src="{lead.meta_creative_media_url}" style="max-width: 300px; max-height: 200px; border-radius: 6px; border: 1px solid #ddd;" alt="Ad Creative"/>
                        <div style="font-size: 12px; color: #6c757d; margin-top: 4px;">🖼️ Image Creative</div>
                    </div>
                    ''')

            # Title
            if lead.meta_creative_title:
                html_parts.append(f'''
                <div style="font-weight: bold; font-size: 16px; color: #333; margin-bottom: 8px;">
                    {lead.meta_creative_title}
                </div>
                ''')

            # Body text
            if lead.meta_creative_body:
                html_parts.append(f'''
                <div style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin-bottom: 10px; line-height: 1.4;">
                    {lead.meta_creative_body}
                </div>
                ''')

            # Call to action
            if lead.meta_creative_cta:
                html_parts.append(f'''
                <div style="text-align: center; margin-top: 12px;">
                    <span style="background: #007bff; color: white; padding: 8px 16px; border-radius: 20px; font-size: 13px; font-weight: 600;">
                        {lead.meta_creative_cta.replace('_', ' ').title()}
                    </span>
                </div>
                ''')

            # Footer
            html_parts.append('''
            <div style="border-top: 1px solid #dee2e6; margin-top: 12px; padding-top: 8px; text-align: center;">
                <small style="color: #6c757d;">📊 Meta Ad Creative Preview</small>
            </div>
            </div>
            ''')

            lead.meta_creative_preview = ''.join(html_parts)

    # ===================================================================
    # Stage change detection → fire CAPI events
    # ===================================================================
    def write(self, vals):
        """Override write to detect stage / won_status changes and fire Meta CAPI events."""
        if self.env.context.get('skip_capi_hook'):
            return super().write(vals)

        old_stages = {}
        old_won = {}
        old_prob = {}
        watch_stage = 'stage_id' in vals
        watch_won = 'won_status' in vals or 'probability' in vals
        if watch_stage or watch_won:
            for lead in self:
                old_stages[lead.id] = lead.stage_id.id if lead.stage_id else False
                old_won[lead.id] = lead.won_status
                old_prob[lead.id] = lead.probability or 0.0

        result = super().write(vals)

        if watch_stage or watch_won:
            for lead in self:
                stage_changed = old_stages.get(lead.id) != (lead.stage_id.id if lead.stage_id else False)
                won_changed = old_won.get(lead.id) != lead.won_status
                became_hot = (old_prob.get(lead.id, 0) < 100) and ((lead.probability or 0) >= 100)
                if stage_changed or won_changed or became_hot:
                    self._check_and_fire_capi_event(lead)

        return result

    def action_set_won(self, *args, **kwargs):
        """Fire Meta Purchase when sales marks the opportunity as Won."""
        result = super().action_set_won(*args, **kwargs)
        for lead in self:
            self._check_and_fire_capi_event(lead)
        return result

    def _check_and_fire_capi_event(self, lead):
        """
        Check whether the lead's current stage should trigger
        a Meta CAPI event, and fire it if so.

        Only fires for leads that originated from Meta
        (have a meta_leadgen_id) OR from the akod.tech website
        (have meta_fbp or meta_fbc or meta_event_source_url).
        """
        # Only fire for leads with Meta origin or website tracking
        is_meta_lead = bool(lead.meta_leadgen_id)
        is_tracked_web_lead = bool(
            lead.meta_fbp or lead.meta_fbc or lead.meta_event_source_url
        )

        if not is_meta_lead and not is_tracked_web_lead:
            return

        stage_name = (lead.stage_id.name or "").lower().strip()

        try:
            from ..services.meta_capi_helpers import fire_capi_for_lead

            is_qualified = bool(stage_name) and self._is_qualified_stage(stage_name)
            is_won = (
                lead.won_status == 'won'
                or (lead.stage_id and lead.stage_id.is_won)
                or (bool(stage_name) and self._is_won_stage(stage_name))
                or (lead.probability or 0) >= 100
            )
            if not is_qualified and not is_won:
                return

            # Qualified → Lead (only if not already sent at form submit)
            if is_qualified and not is_won and not lead.meta_capi_lead_event_sent:
                result = fire_capi_for_lead(self.env, lead, event_name='Lead')
                if result.get('success') and not result.get('skipped'):
                    lead.sudo().with_context(skip_capi_hook=True).write({
                        'meta_capi_event_log': self._append_event_log(
                            lead.meta_capi_event_log, 'Lead', result,
                        ),
                    })
                    _logger.info(
                        "Meta CAPI Lead (qualified) sent for lead %s (stage: %s)",
                        lead.id, lead.stage_id.name,
                    )
                elif not result.get('success'):
                    _logger.error(
                        "Meta CAPI Lead FAILED for lead %s: %s",
                        lead.id, result.get('error'),
                    )

            # Won / sold → Purchase fire-back
            if is_won and not lead.meta_capi_purchase_event_sent:
                value = lead.expected_revenue or None
                result = fire_capi_for_lead(
                    self.env, lead, event_name='Purchase', value=value,
                )
                if result.get('success') and not result.get('skipped'):
                    lead.sudo().with_context(skip_capi_hook=True).write({
                        'meta_capi_event_log': self._append_event_log(
                            lead.meta_capi_event_log, 'Purchase', result,
                        ),
                    })
                    _logger.info(
                        "Meta CAPI Purchase sent for lead %s (stage: %s, value: %s)",
                        lead.id, lead.stage_id.name, value,
                    )
                elif not result.get('success'):
                    _logger.error(
                        "Meta CAPI Purchase FAILED for lead %s: %s",
                        lead.id, result.get('error'),
                    )

        except Exception as exc:
            _logger.error(
                "Exception firing Meta CAPI event for lead %s: %s",
                lead.id, exc, exc_info=True,
            )

    @staticmethod
    def _is_qualified_stage(stage_name_lower):
        """Check if a stage name (lowercase) matches 'qualified' patterns."""
        return any(kw in stage_name_lower for kw in QUALIFIED_STAGE_KEYWORDS)

    @staticmethod
    def _is_won_stage(stage_name_lower):
        """Check if a stage name (lowercase) matches 'won/sold/satisfied' patterns."""
        return any(kw in stage_name_lower for kw in WON_STAGE_KEYWORDS)

    @staticmethod
    def _append_event_log(existing_log, event_name, result):
        """Append a timestamped entry to the CAPI event log."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "SUCCESS" if result.get("success") else "FAILED"
        entry = f"[{timestamp}] {event_name} — {status}"
        if result.get("response"):
            entry += f" — {result['response']}"
        elif result.get("error"):
            entry += f" — {result['error']}"
        entry += "\n"

        if existing_log:
            return existing_log + entry
        return entry

    # ===================================================================
    # Manual CAPI event action (button on form)
    # ===================================================================
    def action_send_capi_lead_event(self):
        """Manually send a Lead event to Meta CAPI."""
        self.ensure_one()
        self._check_and_fire_capi_event(self)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Meta CAPI',
                'message': f'Lead event processing completed. Check the CAPI Event Log for details.',
                'type': 'info',
            },
        }

    # ===================================================================
    # Refresh ad creative (existing functionality)
    # ===================================================================
    def action_refresh_ad_creative(self):
        """Action to manually refresh ad creative data"""
        self.ensure_one()

        if not self.meta_ad_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Ad ID',
                    'message': 'This lead does not have a Meta Ad ID to fetch creative data.',
                    'type': 'warning',
                },
            }

        # Get access token
        access_token = os.environ.get('META_USER_ACCESS_TOKEN')
        if not access_token:
            try:
                ICP = self.env['ir.config_parameter'].sudo()
                access_token = ICP.get_param('meta_leads.access_token')
            except Exception:
                pass

        if not access_token:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Access Token Missing',
                    'message': 'Meta access token is not configured.',
                    'type': 'warning',
                },
            }

        try:
            creative_data = self._fetch_ad_creative_from_meta(self.meta_ad_id, access_token)
            if creative_data:
                self.write(creative_data)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success!',
                        'message': 'Ad creative data has been refreshed successfully.',
                        'type': 'success',
                    },
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'No Data Found',
                        'message': 'Could not fetch ad creative data.',
                        'type': 'warning',
                    },
                }
        except Exception as e:
            _logger.error(f"Error refreshing ad creative: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Error fetching ad creative: {str(e)}',
                    'type': 'danger',
                },
            }

    def _fetch_ad_creative_from_meta(self, ad_id, access_token):
        """Fetch ad creative data from Meta Graph API"""
        try:
            ad_url = f"https://graph.facebook.com/v24.0/{ad_id}"
            ad_params = {
                'access_token': access_token,
                'fields': 'id,name,status,creative{id,object_story_spec,image_url,video_id,thumbnail_url}',
            }

            ad_response = requests.get(ad_url, params=ad_params, timeout=10)
            if ad_response.status_code != 200:
                _logger.error(f"Error fetching ad: {ad_response.status_code} - {ad_response.text}")
                return None

            ad_data = ad_response.json()
            creative_info = ad_data.get('creative', {})

            update_data = {
                'meta_ad_name': ad_data.get('name'),
            }

            if creative_info.get('id'):
                creative_id = creative_info['id']
                creative_url = f"https://graph.facebook.com/v24.0/{creative_id}"
                creative_params = {
                    'access_token': access_token,
                    'fields': 'id,name,object_story_spec,image_url,video_id,thumbnail_url,body,title',
                }

                creative_response = requests.get(creative_url, params=creative_params, timeout=10)
                if creative_response.status_code == 200:
                    creative_data = creative_response.json()

                    media_url = None
                    creative_type = 'image'

                    if creative_data.get('video_id'):
                        creative_type = 'video'
                        media_url = self._get_video_thumbnail_from_meta(
                            creative_data['video_id'], access_token,
                        )
                    elif creative_data.get('image_url'):
                        media_url = creative_data['image_url']
                    elif creative_data.get('thumbnail_url'):
                        media_url = creative_data['thumbnail_url']

                    cta = ""
                    story_spec = creative_data.get('object_story_spec', {})
                    if story_spec.get('page_post_data', {}).get('call_to_action'):
                        cta = story_spec['page_post_data']['call_to_action'].get('type', '')

                    update_data.update({
                        'meta_creative_id': creative_data.get('id'),
                        'meta_creative_type': creative_type,
                        'meta_creative_media_url': media_url,
                        'meta_creative_body': creative_data.get('body'),
                        'meta_creative_title': creative_data.get('title'),
                        'meta_creative_cta': cta,
                    })

            return update_data

        except Exception as e:
            _logger.error(f"Exception fetching ad creative: {str(e)}")
            return None

    def _get_video_thumbnail_from_meta(self, video_id, access_token):
        """Get video thumbnail URL from Meta"""
        try:
            video_url = f"https://graph.facebook.com/v24.0/{video_id}"
            video_params = {
                'access_token': access_token,
                'fields': 'thumbnails.limit(1){uri},picture',
            }

            response = requests.get(video_url, params=video_params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                thumbnails = data.get('thumbnails', {}).get('data', [])
                if thumbnails:
                    return thumbnails[0].get('uri')
                return data.get('picture')

            return None

        except Exception as e:
            _logger.error(f"Error fetching video thumbnail: {str(e)}")
            return None
