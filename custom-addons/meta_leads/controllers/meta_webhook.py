# -*- coding: utf-8 -*-
try:
    from tcrm import http
    from tcrm.http import request
except ImportError:
    from odoo import http
    from odoo.http import request
import json
import logging
import requests
import os
import hashlib
import hmac

_logger = logging.getLogger(__name__)


class MetaLeadWebhook(http.Controller):
    """
    Enhanced Meta Leads webhook with:
    - Real-time ad creative fetching (Meta Lead Forms)
    - Website form ingestion (akod.tech)
    - Automatic fbc/fbp cookie and client IP/UA capture for CAPI
    """

    def _get_meta_access_token(self):
        """Get Meta access token from environment or system parameters"""
        token = os.environ.get('META_USER_ACCESS_TOKEN')
        if token:
            return token

        try:
            IrConfigParameter = request.env['ir.config_parameter'].sudo()
            token = IrConfigParameter.get_param('meta_leads.access_token')
            return token
        except Exception:
            return None

    def _get_meta_pixel_id(self):
        """Get Meta Pixel ID from environment or system parameters"""
        pixel_id = os.environ.get('META_PIXEL_ID')
        if pixel_id:
            return pixel_id

        try:
            IrConfigParameter = request.env['ir.config_parameter'].sudo()
            pixel_id = IrConfigParameter.get_param('meta_leads.pixel_id')
            return pixel_id
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Meta Graph API helpers
    # ------------------------------------------------------------------

    def _fetch_lead_data(self, leadgen_id, access_token):
        """Fetch lead data from Meta Graph API"""
        try:
            url = f"https://graph.facebook.com/v24.0/{leadgen_id}"
            params = {
                'access_token': access_token,
                'fields': 'id,ad_id,adset_id,campaign_id,form_id,page_id,created_time,field_data',
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                _logger.error(f"Error fetching lead data: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            _logger.error(f"Exception fetching lead data: {str(e)}")
            return None

    def _fetch_ad_creative_data(self, ad_id, access_token):
        """Fetch ad creative data from Meta Graph API"""
        try:
            ad_url = f"https://graph.facebook.com/v24.0/{ad_id}"
            ad_params = {
                'access_token': access_token,
                'fields': 'id,name,status,creative{id,object_story_spec,image_url,video_id,thumbnail_url}',
            }

            ad_response = requests.get(ad_url, params=ad_params, timeout=10)
            if ad_response.status_code != 200:
                _logger.error(f"Error fetching ad data: {ad_response.status_code} - {ad_response.text}")
                return None

            ad_data = ad_response.json()
            creative_info = ad_data.get('creative', {})

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
                    return {
                        'ad_id': ad_data.get('id'),
                        'ad_name': ad_data.get('name'),
                        'ad_status': ad_data.get('status'),
                        'creative_id': creative_data.get('id'),
                        'creative_name': creative_data.get('name'),
                        'image_url': creative_data.get('image_url'),
                        'video_id': creative_data.get('video_id'),
                        'thumbnail_url': creative_data.get('thumbnail_url'),
                        'body': creative_data.get('body'),
                        'title': creative_data.get('title'),
                        'object_story_spec': creative_data.get('object_story_spec', {}),
                    }

            return {
                'ad_id': ad_data.get('id'),
                'ad_name': ad_data.get('name'),
                'ad_status': ad_data.get('status'),
                'creative_id': creative_info.get('id'),
                'image_url': creative_info.get('image_url'),
                'video_id': creative_info.get('video_id'),
                'thumbnail_url': creative_info.get('thumbnail_url'),
            }

        except Exception as e:
            _logger.error(f"Exception fetching ad creative: {str(e)}")
            return None

    def _get_video_thumbnail(self, video_id, access_token):
        """Get video thumbnail URL"""
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

    # ------------------------------------------------------------------
    # Field extraction helpers
    # ------------------------------------------------------------------

    def _extract_field_data(self, field_data):
        """Extract and format lead field data"""
        extracted = {
            'name': None,
            'email': None,
            'phone': None,
            'company': None,
            'city': None,
            'message': None,
            'form_answers': [],
        }

        # Field mapping for Turkish and English
        field_mapping = {
            'name': ['full_name', 'name', 'ad_soyad', 'isim_soyisim', 'ad_soyadi', 'tam_ad'],
            'email': ['email', 'e_posta', 'eposta', 'e-posta', 'mail_adresi'],
            'phone': ['phone_number', 'telefon', 'telefon_numarasi', 'phone', 'mobile_phone'],
            'company': ['company_name', 'sirket_adi', 'firma_adi', 'company', 'work_company'],
            'city': ['city', 'sehir', 'il', 'location'],
            'message': ['message', 'mesaj', 'yorum', 'not', 'additional_info'],
        }

        for field in field_data:
            question = field.get('name', '').lower()
            value = field.get('values', [])
            if value:
                value_str = value[0] if isinstance(value, list) else str(value)

                extracted['form_answers'].append({
                    'question': field.get('name', 'Question'),
                    'answer': value_str,
                })

                for field_type, keywords in field_mapping.items():
                    if any(keyword in question for keyword in keywords):
                        if not extracted[field_type]:
                            extracted[field_type] = value_str
                        break

        return extracted

    def _format_form_answers(self, form_answers):
        """Format form answers for display"""
        if not form_answers:
            return "No form responses available"

        formatted = "=== CLIENT FORM RESPONSES ===\n\n"
        for i, answer in enumerate(form_answers, 1):
            formatted += f"{i}. {answer['question']}: {answer['answer']}\n"

        formatted += f"\n--- Form completed with {len(form_answers)} questions ---"
        return formatted

    def _detect_platform(self, campaign_name="", ad_name="", adset_name=""):
        """Detect if lead comes from Instagram or Facebook"""
        text_to_check = f"{campaign_name} {ad_name} {adset_name}".lower()
        instagram_indicators = ['instagram', 'ig_', 'insta_', 'reels', 'stories']

        if any(indicator in text_to_check for indicator in instagram_indicators):
            return 'instagram', 'instagram_ads'
        else:
            return 'facebook', 'facebook_ads'

    def _capture_request_context(self):
        """Capture client IP, user agent, fbc, fbp from the HTTP request."""
        context = {}

        try:
            httprequest = request.httprequest
            # Client IP — check X-Forwarded-For for reverse-proxy setups
            forwarded_for = httprequest.headers.get('X-Forwarded-For')
            if forwarded_for:
                context['client_ip'] = forwarded_for.split(',')[0].strip()
            else:
                context['client_ip'] = httprequest.remote_addr

            # User Agent
            context['user_agent'] = httprequest.headers.get('User-Agent', '')

            # fbc / fbp cookies
            context['fbc'] = httprequest.cookies.get('_fbc', '')
            context['fbp'] = httprequest.cookies.get('_fbp', '')
        except Exception as e:
            _logger.warning(f"Could not capture request context: {e}")

        return context

    # ------------------------------------------------------------------
    # UTM helpers
    # ------------------------------------------------------------------

    def _get_or_create_utm_source(self, source_name):
        """Get or create UTM source"""
        try:
            UTMSource = request.env['utm.source'].sudo()
            source = UTMSource.search([('name', '=', source_name)], limit=1)
            if not source:
                source = UTMSource.create({'name': source_name})
            return source
        except Exception:
            return (
                request.env.ref('utm.utm_source_direct', raise_if_not_found=False)
                or request.env['utm.source'].sudo().create({'name': 'direct'})
            )

    def _get_or_create_utm_medium(self, medium_name):
        """Get or create UTM medium"""
        try:
            UTMMedium = request.env['utm.medium'].sudo()
            medium = UTMMedium.search([('name', '=', medium_name)], limit=1)
            if not medium:
                medium = UTMMedium.create({'name': medium_name})
            return medium
        except Exception:
            return (
                request.env.ref('utm.utm_medium_email', raise_if_not_found=False)
                or request.env['utm.medium'].sudo().create({'name': 'organic'})
            )

    # ==================================================================
    # ENDPOINT 1: Meta Webhook Verify (GET)
    # ==================================================================

    @http.route('/webhook/meta/verify', type='http', auth='public', methods=['GET'], csrf=False)
    def verify_meta_webhook(self, **kwargs):
        """Verify Meta webhook endpoint"""
        verify_token = os.environ.get(
            'META_WEBHOOK_VERIFY_TOKEN', 'my_secure_meta_webhook_token_2024',
        )

        mode = kwargs.get('hub.mode')
        token = kwargs.get('hub.verify_token')
        challenge = kwargs.get('hub.challenge')

        if mode == 'subscribe' and token == verify_token:
            _logger.info('Meta webhook verified successfully')
            return challenge
        else:
            _logger.warning(f'Meta webhook verification failed. Mode: {mode}, Token: {token}')
            return http.Response('Verification failed', status=403)

    # ==================================================================
    # ENDPOINT 2: Meta Lead Forms Webhook (POST)
    # ==================================================================

    @http.route('/webhook/meta/leads', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_meta_lead(self, **kwargs):
        """
        Receive leads from Meta Lead Ads (Facebook/Instagram).

        This handles the real-time webhook from Meta when someone fills
        out a Lead Form inside the Meta platform.
        """
        try:
            data = request.jsonrequest
            _logger.info(f"Received Meta Lead Form webhook: {json.dumps(data, indent=2)}")

            access_token = self._get_meta_access_token()
            if not access_token:
                _logger.error("Meta access token not found")
                return {'success': False, 'error': 'Access token not configured'}

            # Capture request context for CAPI
            ctx = self._capture_request_context()

            leads_created = []

            if data.get('object') == 'page':
                for entry in data.get('entry', []):
                    for change in entry.get('changes', []):
                        if change.get('field') == 'leadgen':
                            value = change.get('value', {})
                            leadgen_id = value.get('leadgen_id')
                            ad_id = value.get('ad_id')

                            if not leadgen_id:
                                continue

                            _logger.info(f"Processing Meta lead: {leadgen_id}, ad: {ad_id}")

                            # Fetch full lead data from Meta
                            lead_data = self._fetch_lead_data(leadgen_id, access_token)
                            if not lead_data:
                                _logger.error(f"Could not fetch lead data for {leadgen_id}")
                                continue

                            # Extract field data
                            field_data = lead_data.get('field_data', [])
                            extracted = self._extract_field_data(field_data)

                            # Fetch ad creative data
                            creative_data = None
                            if ad_id:
                                creative_data = self._fetch_ad_creative_data(ad_id, access_token)

                            # Detect platform
                            ad_name = creative_data.get('ad_name', '') if creative_data else ''
                            source, medium = self._detect_platform("", ad_name)

                            # Prepare lead data
                            lead_name = extracted.get('name') or f"Meta Lead - {leadgen_id}"

                            odoo_lead_data = {
                                'name': lead_name,
                                'contact_name': extracted.get('name'),
                                'email_from': extracted.get('email'),
                                'phone': extracted.get('phone'),
                                'partner_name': extracted.get('company'),
                                'city': extracted.get('city'),
                                'description': extracted.get('message', ''),
                                'type': 'lead',

                                # Meta specific fields
                                'meta_leadgen_id': leadgen_id,
                                'meta_ad_id': ad_id,
                                'meta_adset_id': lead_data.get('adset_id'),
                                'meta_campaign_id': lead_data.get('campaign_id'),
                                'meta_form_id': lead_data.get('form_id'),
                                'meta_page_id': lead_data.get('page_id'),
                                'meta_platform': source,
                                'meta_form_answers': self._format_form_answers(extracted['form_answers']),
                                'meta_raw_payload': json.dumps(data, indent=2),

                                # UTM tracking
                                'source_id': self._get_or_create_utm_source(source).id,
                                'medium_id': self._get_or_create_utm_medium(medium).id,

                                # CAPI tracking context
                                'meta_client_ip': ctx.get('client_ip'),
                                'meta_client_user_agent': ctx.get('user_agent'),
                                'meta_fbc': ctx.get('fbc'),
                                'meta_fbp': ctx.get('fbp'),
                                'meta_event_source_url': 'https://www.facebook.com',
                            }

                            # Add creative data if available
                            if creative_data:
                                media_url = None
                                if creative_data.get('image_url'):
                                    media_url = creative_data['image_url']
                                elif creative_data.get('video_id'):
                                    media_url = self._get_video_thumbnail(
                                        creative_data['video_id'], access_token,
                                    )
                                elif creative_data.get('thumbnail_url'):
                                    media_url = creative_data['thumbnail_url']

                                odoo_lead_data.update({
                                    'meta_ad_name': creative_data.get('ad_name'),
                                    'meta_creative_id': creative_data.get('creative_id'),
                                    'meta_creative_body': creative_data.get('body'),
                                    'meta_creative_title': creative_data.get('title'),
                                    'meta_creative_media_url': media_url,
                                    'meta_creative_type': (
                                        'video' if creative_data.get('video_id') else 'image'
                                    ),
                                })

                                story_spec = creative_data.get('object_story_spec', {})
                                if story_spec.get('page_post_data', {}).get('call_to_action'):
                                    cta = story_spec['page_post_data']['call_to_action']
                                    odoo_lead_data['meta_creative_cta'] = cta.get('type', '')

                            # -------------------------------------------
                            # Fire immediate Lead event to CAPI
                            # (lead form submission = Lead event)
                            # -------------------------------------------
                            self._fire_initial_lead_event(odoo_lead_data, ctx)

                            # Create lead in Odoo
                            lead = request.env['crm.lead'].sudo().create(odoo_lead_data)
                            leads_created.append(lead.id)

                            _logger.info(f"Created Meta lead {lead.id}: {lead.name}")

            return {
                'success': True,
                'leads_created': leads_created,
                'count': len(leads_created),
            }

        except Exception as e:
            _logger.error(f"Error processing Meta webhook: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    # ==================================================================
    # ENDPOINT 3: Website Form Webhook (POST)
    #   — for akod.tech contact/inquiry forms
    # ==================================================================

    def _get_akod_webhook_secret(self):
        """Get webhook secret from environment or system parameters."""
        secret = os.environ.get('AKOD_WEBHOOK_SECRET')
        if secret:
            return secret
        try:
            return request.env['ir.config_parameter'].sudo().get_param('meta_leads.akod_webhook_secret')
        except Exception:
            return None

    def _verify_webhook_security(self, raw_bytes, headers):
        """Verify HMAC signature or secret header if secret is configured."""
        secret = self._get_akod_webhook_secret()
        if not secret:
            return True, None

        provided_token = (
            headers.get('X-Akod-Secret')
            or headers.get('X-Webhook-Secret')
            or headers.get('X-Akod-Token')
        )
        if provided_token and hmac.compare_digest(provided_token, secret):
            return True, None

        provided_sig = headers.get('X-Akod-Signature') or headers.get('X-Hub-Signature-256')
        if provided_sig and raw_bytes:
            sig_parts = provided_sig.split('=', 1)
            sig_val = sig_parts[1] if len(sig_parts) == 2 else provided_sig
            expected_sig = hmac.new(secret.encode('utf-8'), raw_bytes, hashlib.sha256).hexdigest()
            if hmac.compare_digest(sig_val, expected_sig):
                return True, None

        return False, "Invalid or missing webhook signature/secret"

    def _resolve_tenant_lead_defaults(self, data):
        """
        Dynamically resolve valid type, company, stage, sales team, and user
        for the current tenant database without hardcoded IDs.
        """
        env = request.env
        IrConfigParameter = env['ir.config_parameter'].sudo()

        # 1. Lead type ('lead' by default so it appears in Lead Havuzu)
        lead_type = IrConfigParameter.get_param('meta_leads.default_type', 'lead')
        if lead_type not in ('lead', 'opportunity'):
            lead_type = 'lead'

        # 2. Target Company (current company in current tenant DB)
        company = env.company or env['res.company'].sudo().search([], limit=1)
        company_id = company.id if company else False

        # 3. Configured or Default Sales Team
        team_id = False
        cfg_team_str = IrConfigParameter.get_param('meta_leads.default_team_id')
        if cfg_team_str and cfg_team_str.isdigit():
            team = env['crm.team'].sudo().search([
                ('id', '=', int(cfg_team_str)),
                ('active', '=', True),
            ], limit=1)
            if team and (not team.company_id or team.company_id.id == company_id):
                team_id = team.id

        if not team_id:
            domain = [('active', '=', True)]
            if company_id:
                domain = ['|', ('company_id', '=', False), ('company_id', '=', company_id)] + domain
            team = env['crm.team'].sudo().search(domain, order='sequence asc, id asc', limit=1)
            if team:
                team_id = team.id

        # 4. Configured or Default Salesperson (User)
        user_id = False
        cfg_user_str = IrConfigParameter.get_param('meta_leads.default_user_id')
        if cfg_user_str and cfg_user_str.isdigit():
            user = env['res.users'].sudo().search([
                ('id', '=', int(cfg_user_str)),
                ('active', '=', True),
            ], limit=1)
            if user and (not user.company_id or user.company_id.id == company_id or company_id in user.company_ids.ids):
                user_id = user.id

        # 5. Valid Stage for current DB
        stage_id = False
        cfg_stage_str = IrConfigParameter.get_param('meta_leads.default_stage_id')
        if cfg_stage_str and cfg_stage_str.isdigit():
            stage = env['crm.stage'].sudo().search([('id', '=', int(cfg_stage_str))], limit=1)
            if stage:
                stage_id = stage.id

        if not stage_id:
            stages = env['crm.stage'].sudo().search([], order='sequence asc, id asc')
            if stages:
                stage_id = stages[0].id

        return {
            'type': lead_type,
            'company_id': company_id,
            'team_id': team_id,
            'user_id': user_id,
            'stage_id': stage_id,
        }

    def _find_existing_duplicate_lead(self, data, idempotency_key=None, env=None):
        """Search for an existing lead to guarantee idempotency."""
        LeadModel = env
        if LeadModel is None or not hasattr(LeadModel, 'search'):
            try:
                LeadModel = request.env['crm.lead'].sudo()
            except Exception:
                LeadModel = None

        if LeadModel is None:
            return None


        if idempotency_key:
            try:
                if hasattr(LeadModel, 'flush_model'):
                    LeadModel.flush_model()
                if hasattr(LeadModel, 'env') and hasattr(LeadModel.env, 'flush_all'):
                    LeadModel.env.flush_all()
            except Exception:
                pass
            domain = [
                '|',
                ('meta_leadgen_id', '=', str(idempotency_key)),
                ('description', 'ilike', f"%IDEMPOTENCY_KEY:{idempotency_key}%"),
            ]
            res_found = LeadModel.search(domain, order='create_date desc, id desc', limit=1)
            if res_found:
                return res_found










        email = data.get('email')
        phone = data.get('phone')
        if email or phone:
            domain = []
            if email:
                domain.append(('email_from', '=', email))
            if phone:
                domain.append(('phone', '=', phone))
            if domain:
                existing = LeadModel.search(domain, order='create_date desc', limit=1)
                if existing and existing.create_date:

                    from datetime import datetime, timedelta
                    if existing.create_date > datetime.utcnow() - timedelta(seconds=120):
                        return existing


        return None


    @http.route(
        '/webhook/akod/lead/legacy',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def receive_akod_website_lead(self, **kwargs):
        """
        Receive leads from the akod.tech website forms.
        """
        try:
            # 1. Payload size limit (max 1MB)
            content_len = request.httprequest.content_length
            if content_len and content_len > 1024 * 1024:
                return request.make_json_response(
                    {'success': False, 'error': 'Payload size exceeds 1MB limit'},
                    status=413,
                )

            raw_bytes = request.httprequest.data or b''

            # 2. Security / HMAC verification
            is_valid_sec, sec_err = self._verify_webhook_security(
                raw_bytes, request.httprequest.headers,
            )
            if not is_valid_sec:
                _logger.warning(f"Rejected akod.tech webhook request: {sec_err}")
                return request.make_json_response(
                    {'success': False, 'error': sec_err},
                    status=401,
                )

            data = None
            try:
                data = request.get_json_data()
            except Exception:
                pass

            if not data:
                try:
                    raw_data = raw_bytes.decode('utf-8', errors='replace')
                    data = json.loads(raw_data, strict=False) if raw_data else {}
                except Exception:
                    data = request.params or {}

            if not isinstance(data, dict):
                data = {}

            _logger.info(f"Received akod.tech website lead: {json.dumps(data, indent=2)}")

            # 3. Idempotency Key check
            idempotency_key = (
                data.get('idempotency_key')
                or data.get('submission_id')
                or data.get('submission_uuid')
                or request.httprequest.headers.get('X-Idempotency-Key')
            )

            existing_lead = self._find_existing_duplicate_lead(data, idempotency_key)
            if existing_lead:
                _logger.info(
                    f"Duplicate akod.tech lead submission for key {idempotency_key}. "
                    f"Returning existing lead ID: {existing_lead.id}"
                )
                return request.make_json_response({
                    'success': True,
                    'lead_id': existing_lead.id,
                    'duplicate': True,
                    'message': f'Lead "{existing_lead.name}" already processed',
                })

            # 4. Resolve dynamic tenant defaults (NO hardcoded IDs)
            tenant_defaults = self._resolve_tenant_lead_defaults(data)

            # Capture request context
            ctx = self._capture_request_context()

            # Build lead data
            lead_name = data.get('name', 'Website Lead')

            desc = data.get('message', '')
            if idempotency_key:
                desc += f"\n\nIDEMPOTENCY_KEY:{idempotency_key}"

            odoo_lead_data = {
                'name': lead_name,
                'contact_name': data.get('name'),
                'email_from': data.get('email'),
                'phone': data.get('phone'),
                'partner_name': data.get('company'),
                'city': data.get('city'),
                'description': desc,
                'type': tenant_defaults['type'],
                'user_id': tenant_defaults['user_id'],
                'team_id': tenant_defaults['team_id'],
                'stage_id': tenant_defaults['stage_id'],
                'company_id': tenant_defaults['company_id'],

                # Source tracking
                'meta_platform': 'website',
                'meta_source': 'akod_website',
                'meta_medium': 'organic',

                # CAPI tracking
                'meta_client_ip': ctx.get('client_ip'),
                'meta_client_user_agent': ctx.get('user_agent'),
                'meta_fbc': data.get('fbc') or ctx.get('fbc'),
                'meta_fbp': data.get('fbp') or ctx.get('fbp'),
                'meta_event_source_url': data.get('page_url', 'https://akod.tech'),

                # Form answers
                'meta_form_answers': self._format_website_form_answers(data),
                'meta_raw_payload': json.dumps(data, indent=2),
            }

            if idempotency_key:
                odoo_lead_data['meta_leadgen_id'] = str(idempotency_key)

            # UTM tracking from form data
            utm_source = data.get('utm_source', 'akod_website')
            utm_medium = data.get('utm_medium', 'organic')
            odoo_lead_data['source_id'] = self._get_or_create_utm_source(utm_source).id
            odoo_lead_data['medium_id'] = self._get_or_create_utm_medium(utm_medium).id

            # 5. Create local CRM lead in tenant database
            lead = request.env['crm.lead'].sudo().create(odoo_lead_data)
            _logger.info(f'Created akod.tech website lead with ID: {lead.id} in tenant DB: {request.db}')

            # Guarantee local transaction commit
            try:
                request.env.cr.commit()
            except Exception as commit_err:
                _logger.warning(f"Explicit cr.commit warning: {commit_err}")

            # 6. Decoupled Meta CAPI execution (isolated try/except)
            try:
                self._fire_initial_lead_event(odoo_lead_data, ctx)
                pixel_id = self._get_meta_pixel_id()
                access_token = self._get_meta_access_token()
                if pixel_id and access_token:
                    from ..services.meta_capi_service import MetaCAPIService
                    capi = MetaCAPIService(pixel_id, access_token)
                    result = capi.send_lead_event(lead)
                    _logger.info(f"CAPI Lead event result for lead {lead.id}: {result}")
            except Exception as capi_err:
                _logger.error(f"Failed sending CAPI Lead event (lead {lead.id} saved successfully): {str(capi_err)}")

            return request.make_json_response({
                'success': True,
                'lead_id': lead.id,
                'message': f'Lead "{lead.name}" created successfully',
            })

        except Exception as e:
            _logger.error(f"Error processing akod.tech lead: {str(e)}", exc_info=True)
            return request.make_json_response(
                {'success': False, 'error': str(e)},
                status=500,
            )


    def _format_website_form_answers(self, data):
        """Format website form data as readable text."""
        # Exclude internal fields
        skip_fields = {'fbc', 'fbp', 'page_url', 'utm_source', 'utm_medium', 'utm_campaign'}
        answers = []
        for key, value in data.items():
            if key not in skip_fields and value:
                answers.append(f"  • {key.replace('_', ' ').title()}: {value}")

        if not answers:
            return "No form data available"

        header = "=== AKOD.TECH WEBSITE FORM ===\n\n"
        return header + "\n".join(answers) + f"\n\n--- {len(answers)} fields submitted ---"

    # ------------------------------------------------------------------
    # Fire initial Lead event to CAPI on form submission
    # ------------------------------------------------------------------

    def _fire_initial_lead_event(self, lead_data, ctx):
        """
        Fire a 'Lead' event to Meta CAPI immediately when a form is submitted.
        This happens before the Odoo lead record is created.

        This gives Meta the earliest possible signal for optimisation.
        """
        try:
            pixel_id = self._get_meta_pixel_id()
            access_token = self._get_meta_access_token()

            if not pixel_id or not access_token:
                _logger.info("Meta CAPI not configured — skipping initial Lead event")
                return

            from ..services.meta_capi_service import MetaCAPIService, _hash_value, _hash_phone

            import time as _time
            import uuid

            capi = MetaCAPIService(pixel_id, access_token)

            # Build user_data manually since we don't have an ORM record yet
            user_data = {}

            em = _hash_value(lead_data.get('email_from'))
            if em:
                user_data['em'] = [em]

            ph = _hash_phone(lead_data.get('phone'))
            if ph:
                user_data['ph'] = [ph]

            name = lead_data.get('contact_name') or lead_data.get('name', '')
            if name:
                parts = name.strip().split(None, 1)
                fn = _hash_value(parts[0]) if len(parts) >= 1 else None
                ln = _hash_value(parts[1]) if len(parts) >= 2 else None
                if fn:
                    user_data['fn'] = [fn]
                if ln:
                    user_data['ln'] = [ln]

            city_val = lead_data.get('city') or 'Istanbul'
            ct = _hash_value(city_val)
            if ct:
                user_data['ct'] = [ct]
                user_data['st'] = [ct]

            co = _hash_value('tr')
            if co:
                user_data['country'] = [co]

            # Non-hashed fields
            if ctx.get('client_ip'):
                user_data['client_ip_address'] = ctx['client_ip']
            if ctx.get('user_agent'):
                user_data['client_user_agent'] = ctx['user_agent']
            if lead_data.get('meta_fbc'):
                user_data['fbc'] = lead_data['meta_fbc']
            if lead_data.get('meta_fbp'):
                user_data['fbp'] = lead_data['meta_fbp']

            event = {
                'event_name': 'Lead',
                'event_time': int(_time.time()),
                'event_id': f"lead_submit_{uuid.uuid4().hex[:12]}",
                'event_source_url': lead_data.get('meta_event_source_url', 'https://akod.tech'),
                'action_source': 'website',
                'opt_out': False,
                'data_processing_options': [],
                'user_data': user_data,
                'custom_data': {
                    'content_name': lead_data.get('name', 'Website Lead'),
                    'content_category': 'lead',
                    'content_type': 'product',
                    'status': 'submitted',
                },
            }

            # If the lead came from Meta ads, include campaign data
            if lead_data.get('meta_campaign_id'):
                event['custom_data']['campaign_id'] = lead_data['meta_campaign_id']
            if lead_data.get('meta_ad_id'):
                event['custom_data']['ad_id'] = lead_data['meta_ad_id']
            if lead_data.get('meta_form_id'):
                event['custom_data']['form_id'] = lead_data['meta_form_id']

            result = capi._send_events([event])

            if result.get('success'):
                _logger.info("✅ Initial Lead CAPI event sent for form submission")
                # Mark the lead data so we don't double-fire
                lead_data['meta_capi_lead_event_sent'] = True
                lead_data['meta_capi_last_event'] = 'Lead'
            else:
                _logger.error("❌ Initial Lead CAPI event failed: %s", result.get('error'))

        except Exception as exc:
            _logger.error("Exception firing initial Lead CAPI event: %s", exc, exc_info=True)

    # ==================================================================
    # ENDPOINT 4: Test endpoint
    # ==================================================================

    @http.route('/webhook/meta/test', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def test_meta_webhook(self, **kwargs):
        """Test endpoint for Meta webhook"""
        access_token = self._get_meta_access_token()
        pixel_id = self._get_meta_pixel_id()

        result = {
            'status': 'ok',
            'message': 'Meta webhook endpoint is working',
            'access_token_configured': bool(access_token),
            'pixel_id_configured': bool(pixel_id),
            'pixel_id': pixel_id,
            'endpoints': {
                'verify': '/webhook/meta/verify (GET)',
                'meta_leads': '/webhook/meta/leads (POST)',
                'akod_website': '/webhook/akod/lead (POST)',
                'test': '/webhook/meta/test (GET/POST)',
            },
        }

        return http.Response(
            json.dumps(result, indent=2),
            content_type='application/json',
        )