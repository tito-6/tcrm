# -*- coding: utf-8 -*-
"""Public JSON lead intake for akod.tech (and other external forms)."""
import json
import logging
import re
import time
import uuid

from tcrm import http
from tcrm.http import request

_logger = logging.getLogger(__name__)

_ALLOWED_ORIGINS = (
    'https://akod.tech',
    'https://www.akod.tech',
    'http://localhost:4321',
    'http://127.0.0.1:4321',
)

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _cors_headers(origin):
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'no-store',
    }
    if origin in _ALLOWED_ORIGINS:
        headers['Access-Control-Allow-Origin'] = origin
        headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Api-Key'
        headers['Vary'] = 'Origin'
    return headers


def _json_response(payload, status=200, origin=None):
    return request.make_response(
        json.dumps(payload, ensure_ascii=False),
        headers=list(_cors_headers(origin).items()),
        status=status,
    )


def _parse_body():
    raw = request.httprequest.get_data(as_text=True) or ''
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _check_api_key():
    expected = (request.env['ir.config_parameter'].sudo()
                .get_param('tcrm_web_enhance.akod_lead_api_key') or '').strip()
    if not expected:
        return True
    auth = request.httprequest.headers.get('Authorization', '')
    header_key = request.httprequest.headers.get('X-Api-Key', '')
    bearer = auth[7:].strip() if auth.lower().startswith('bearer ') else ''
    return header_key == expected or bearer == expected


def _apply_meta_tracking(vals, data):
    """Attach Meta CAPI match params from payload / request (real values only)."""
    try:
        from tcrm.addons.meta_leads.services.meta_capi_helpers import capture_browser_context
    except Exception:
        try:
            from odoo.addons.meta_leads.services.meta_capi_helpers import capture_browser_context
        except Exception:
            return vals, None

    ctx = capture_browser_context(data=data, httprequest=request.httprequest)
    Lead = request.env['crm.lead'].sudo()
    for key in (
        'meta_fbc', 'meta_fbp', 'meta_client_ip', 'meta_client_user_agent',
        'meta_event_source_url', 'meta_event_id', 'city', 'zip',
    ):
        if key in Lead._fields and ctx.get(key):
            vals[key] = ctx[key]

    if not vals.get('meta_event_id'):
        vals['meta_event_id'] = f'evt_akod_{uuid.uuid4().hex[:16]}'

    # Country Many2one from real ISO code only
    country_code = ctx.get('_country_code')
    if country_code and 'country_id' in Lead._fields:
        country = request.env['res.country'].sudo().search(
            [('code', '=ilike', country_code)], limit=1
        )
        if country:
            vals['country_id'] = country.id

    if ctx.get('_gender') and 'meta_gender' in Lead._fields:
        g = ctx['_gender'][:1]
        if g in ('m', 'f'):
            vals['meta_gender'] = g

    if ctx.get('_dob') and 'meta_date_of_birth' in Lead._fields:
        raw = str(ctx['_dob']).strip()
        # Accept YYYY-MM-DD or YYYYMMDD only (Meta format after normalize)
        digits = ''.join(c for c in raw if c.isdigit())
        try:
            if len(digits) == 8:
                vals['meta_date_of_birth'] = f'{digits[0:4]}-{digits[4:6]}-{digits[6:8]}'
            elif len(raw) == 10 and raw[4] == '-' and raw[7] == '-':
                vals['meta_date_of_birth'] = raw
        except Exception:
            pass

    return vals, ctx


class AkodLeadApiController(http.Controller):

    @http.route(
        ['/api/akod/lead', '/api/lead'],
        type='http',
        auth='public',
        methods=['OPTIONS'],
        csrf=False,
        website=True,
    )
    def akod_lead_options(self, **kw):
        origin = request.httprequest.headers.get('Origin')
        return request.make_response(b'', headers=list(_cors_headers(origin).items()), status=204)

    @http.route(
        ['/api/akod/lead', '/api/lead'],
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        website=True,
    )
    def akod_lead_create(self, **kw):
        origin = request.httprequest.headers.get('Origin')
        if not _check_api_key():
            return _json_response({'ok': False, 'error': 'Unauthorized'}, status=401, origin=origin)

        data = _parse_body()
        if data is None:
            return _json_response({'ok': False, 'error': 'Invalid JSON body'}, status=400, origin=origin)

        if str(data.get('companyWebsite') or '').strip():
            return _json_response({'ok': True, 'lead_id': 'ignored', 'event_id': ''}, origin=origin)

        name = str(data.get('name') or data.get('contact_name') or '').strip()
        email = str(data.get('email') or data.get('email_from') or '').strip()
        phone = str(data.get('phone') or '').strip()
        company = str(data.get('company') or data.get('partner_name') or '').strip()
        message = str(
            data.get('message') or data.get('projectDescription') or data.get('description') or ''
        ).strip()
        service = str(data.get('service') or data.get('serviceInterest') or '').strip()
        budget = str(data.get('budget') or data.get('budgetRange') or '').strip()
        page_url = str(data.get('pageUrl') or data.get('page_url') or '').strip()
        utm_source = str(data.get('utmSource') or data.get('utm_source') or '').strip()
        utm_medium = str(data.get('utmMedium') or data.get('utm_medium') or '').strip()
        utm_campaign = str(data.get('utmCampaign') or data.get('utm_campaign') or '').strip()

        if not name or not email or not _EMAIL_RE.match(email):
            return _json_response(
                {'ok': False, 'error': 'name and valid email are required'},
                status=400,
                origin=origin,
            )

        desc_parts = []
        if service:
            desc_parts.append(f'Service: {service}')
        if budget:
            desc_parts.append(f'Budget: {budget}')
        if page_url:
            desc_parts.append(f'Page: {page_url}')
        if message:
            desc_parts.append(message)

        lead_name = f"AKOD Web: {company or name}"
        if service:
            lead_name = f"AKOD Web ({service}): {company or name}"

        vals = {
            'name': lead_name,
            'contact_name': name,
            'email_from': email,
            'phone': phone or False,
            'partner_name': company or False,
            'description': '\n'.join(desc_parts) or False,
            'type': 'lead',
        }

        Lead = request.env['crm.lead'].sudo()
        lead_fields = Lead._fields
        if 'source_id' in lead_fields:
            source_name = utm_source or 'akod.tech'
            source = request.env['utm.source'].sudo().search([('name', '=', source_name)], limit=1)
            if not source:
                source = request.env['utm.source'].sudo().create({'name': source_name})
            vals['source_id'] = source.id
        if utm_medium and 'medium_id' in lead_fields:
            medium = request.env['utm.medium'].sudo().search([('name', '=', utm_medium)], limit=1)
            if not medium:
                medium = request.env['utm.medium'].sudo().create({'name': utm_medium})
            vals['medium_id'] = medium.id
        if utm_campaign and 'campaign_id' in lead_fields:
            campaign = request.env['utm.campaign'].sudo().search([('name', '=', utm_campaign)], limit=1)
            if not campaign:
                campaign = request.env['utm.campaign'].sudo().create({'name': utm_campaign})
            vals['campaign_id'] = campaign.id

        vals, _ctx = _apply_meta_tracking(vals, data)
        event_id = vals.get('meta_event_id') or f'evt_akod_{int(time.time())}'

        try:
            lead = Lead.create(vals)
        except Exception:
            _logger.exception('Failed to create CRM lead from akod.tech form')
            return _json_response({'ok': False, 'error': 'Lead creation failed'}, status=500, origin=origin)

        # Immediate CAPI Lead (redundant with Pixel via shared event_id)
        try:
            from tcrm.addons.meta_leads.services.meta_capi_helpers import fire_capi_for_lead
            fire_capi_for_lead(request.env, lead, event_name='Lead', event_id=event_id)
        except Exception:
            _logger.exception('Meta CAPI Lead fire failed for lead %s', lead.id)

        return _json_response(
            {'ok': True, 'lead_id': f'tcrm_{lead.id}', 'event_id': event_id, 'id': lead.id},
            origin=origin,
        )
