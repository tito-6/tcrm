# -*- coding: utf-8 -*-
"""Shared helpers for Meta CAPI click-ID capture and credential loading."""
from __future__ import annotations

import logging
import os
import time
from urllib.parse import parse_qs, urlparse

_logger = logging.getLogger(__name__)


def build_fbc(fbclid=None, fbc=None, creation_time=None):
    """Return a valid Meta fbc value: fb.1.<creation_time>.<fbclid>."""
    if fbc and str(fbc).startswith('fb.'):
        return str(fbc).strip()
    fbclid = (fbclid or '').strip()
    if not fbclid:
        return False
    if fbclid.startswith('fb.'):
        return fbclid
    ts = int(creation_time or time.time())
    return f'fb.1.{ts}.{fbclid}'


def extract_fbclid_from_url(url):
    if not url:
        return ''
    try:
        qs = parse_qs(urlparse(url).query)
        vals = qs.get('fbclid') or []
        return (vals[0] or '').strip()
    except Exception:
        return ''


def capture_browser_context(data=None, httprequest=None):
    """
    Build tracking fields from JSON body + HTTP request.
    Real values only — never invents city/country/DOB.
    """
    data = data or {}
    req = httprequest
    cookies = getattr(req, 'cookies', {}) if req else {}
    headers = getattr(req, 'headers', {}) if req else {}

    page_url = str(
        data.get('pageUrl')
        or data.get('page_url')
        or data.get('event_source_url')
        or data.get('website')
        or ''
    ).strip()

    fbp = str(
        data.get('fbp')
        or data.get('meta_fbp')
        or data.get('x_fbp')
        or cookies.get('_fbp')
        or ''
    ).strip()

    fbc_raw = (
        data.get('fbc')
        or data.get('meta_fbc')
        or data.get('x_fbc')
        or cookies.get('_fbc')
        or ''
    )
    fbclid = (
        data.get('fbclid')
        or data.get('fb_clid')
        or data.get('x_fbclid')
        or extract_fbclid_from_url(page_url)
        or ''
    )
    fbc = build_fbc(fbclid=fbclid, fbc=fbc_raw) or ''

    client_ip = str(
        data.get('client_ip')
        or data.get('clientIp')
        or data.get('ip')
        or ''
    ).strip()
    if not client_ip and headers:
        xff = headers.get('X-Forwarded-For') or headers.get('X-Real-IP') or ''
        client_ip = xff.split(',')[0].strip() if xff else ''
    if not client_ip and req is not None:
        client_ip = getattr(req, 'remote_addr', '') or ''

    user_agent = str(
        data.get('client_user_agent')
        or data.get('userAgent')
        or data.get('user_agent')
        or (headers.get('User-Agent') if headers else '')
        or ''
    ).strip()

    event_id = str(
        data.get('event_id')
        or data.get('eventId')
        or data.get('browser_event_id')
        or ''
    ).strip()

    city = str(data.get('city') or data.get('ct') or '').strip()
    zip_code = str(data.get('zip') or data.get('postcode') or data.get('zp') or '').strip()
    country = str(data.get('country') or data.get('country_code') or '').strip().lower()
    gender = str(data.get('gender') or data.get('ge') or '').strip().lower()
    dob = str(data.get('date_of_birth') or data.get('dob') or data.get('db') or '').strip()

    return {
        'meta_fbc': fbc or False,
        'meta_fbp': fbp or False,
        'meta_client_ip': client_ip or False,
        'meta_client_user_agent': user_agent or False,
        'meta_event_source_url': page_url or False,
        'meta_event_id': event_id or False,
        'city': city or False,
        'zip': zip_code or False,
        '_country_code': country or False,
        '_gender': gender or False,
        '_dob': dob or False,
        '_fbclid': str(fbclid).strip() or False,
    }


def get_capi_credentials(env):
    pixel_id = os.environ.get('META_PIXEL_ID')
    access_token = os.environ.get('META_USER_ACCESS_TOKEN')
    try:
        ICP = env['ir.config_parameter'].sudo()
        pixel_id = pixel_id or ICP.get_param('meta_leads.pixel_id')
        access_token = access_token or ICP.get_param('meta_leads.access_token')
        if not access_token:
            access_token = ICP.get_param('custom_crm_integration.meta_user_access_token')
    except Exception:
        pass
    return (pixel_id or '').strip(), (access_token or '').strip()


def fire_capi_for_lead(env, lead, event_name='Lead', event_id=None, value=None):
    """Send a CAPI event for a lead. Deduplicates via sent flags."""
    from .meta_capi_service import MetaCAPIService

    try:
        from tcrm import fields as tfields
    except ImportError:
        from odoo import fields as tfields

    pixel_id, access_token = get_capi_credentials(env)
    if not pixel_id or not access_token:
        _logger.warning('Meta CAPI credentials missing — skip %s for lead %s', event_name, lead.id)
        return {'success': False, 'error': 'credentials_missing'}

    if event_name == 'Lead' and getattr(lead, 'meta_capi_lead_event_sent', False):
        return {'success': True, 'skipped': True, 'reason': 'already_sent'}
    if event_name == 'Purchase' and getattr(lead, 'meta_capi_purchase_event_sent', False):
        return {'success': True, 'skipped': True, 'reason': 'already_sent'}

    try:
        capi = MetaCAPIService(pixel_id, access_token)
        source_url = getattr(lead, 'meta_event_source_url', None) or None
        stored_event_id = event_id or getattr(lead, 'meta_event_id', None) or None
        has_web = bool(lead.meta_fbc or lead.meta_fbp or source_url or lead.meta_client_user_agent)
        action_source = 'website' if has_web else 'system_generated'

        if event_name == 'Purchase':
            result = capi.send_purchase_event(
                lead,
                value=value if value is not None else (lead.expected_revenue or None),
                currency='TRY',
                event_source_url=source_url,
                event_id=stored_event_id,
                action_source=action_source,
            )
        else:
            result = capi.send_lead_event(
                lead,
                event_source_url=source_url,
                event_id=stored_event_id,
                action_source=action_source,
            )

        if result.get('success'):
            vals = {
                'meta_capi_last_event': event_name,
                'meta_capi_last_event_time': tfields.Datetime.now(),
            }
            if event_name == 'Lead':
                vals['meta_capi_lead_event_sent'] = True
            elif event_name == 'Purchase':
                vals['meta_capi_purchase_event_sent'] = True
            lead.sudo().with_context(skip_capi_hook=True).write(vals)
        return result
    except Exception as exc:
        _logger.exception('CAPI %s failed for lead %s: %s', event_name, lead.id, exc)
        return {'success': False, 'error': str(exc)}
