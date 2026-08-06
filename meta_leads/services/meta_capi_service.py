# -*- coding: utf-8 -*-
"""
Meta Conversion API (CAPI) Service
===================================
Sends server-side conversion events to Meta via the Conversions API.

Endpoint: POST https://graph.facebook.com/v24.0/{pixel_id}/events
Docs: https://developers.facebook.com/docs/marketing-api/conversions-api

Supported events:
  - Lead          — when a lead is qualified
  - Purchase      — when a lead is sold / satisfied (closed-won)

All PII (email, phone, name, city, etc.) is SHA-256 hashed before sending,
as required by Meta's data processing guidelines.
"""

import hashlib
import json
import logging
import time
import uuid

import requests

_logger = logging.getLogger(__name__)

META_GRAPH_API_VERSION = "v24.0"
META_GRAPH_BASE_URL = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}"


# ---------------------------------------------------------------------------
# PII Hashing helpers (Meta requires lowercase + SHA-256)
# ---------------------------------------------------------------------------

def _hash_value(value):
    """SHA-256 hash a value after normalising (lowercase, strip).
    Returns None if value is falsy."""
    if not value:
        return None
    normalised = str(value).strip().lower()
    if not normalised:
        return None
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def _hash_phone(phone):
    """Normalise phone for Meta: digits only, NO leading +, no spaces/dashes, then hash."""
    if not phone:
        return None
    # Strip everything except numeric digits
    digits_only = "".join(c for c in str(phone) if c.isdigit())
    if not digits_only:
        return None
    # Ensure Turkish country code 90 if starting with 05 or 5
    if len(digits_only) == 10 and digits_only.startswith("5"):
        digits_only = f"90{digits_only}"
    elif len(digits_only) == 11 and digits_only.startswith("05"):
        digits_only = f"90{digits_only[1:]}"
    return hashlib.sha256(digits_only.encode("utf-8")).hexdigest()


def _split_name(full_name):
    """Split 'First Last' into (first, last).  Returns (None, None) if empty."""
    if not full_name:
        return None, None
    parts = full_name.strip().split(None, 1)
    first = parts[0] if len(parts) >= 1 else None
    last = parts[1] if len(parts) >= 2 else None
    return first, last


# ---------------------------------------------------------------------------
# Main service class
# ---------------------------------------------------------------------------

class MetaCAPIService:
    """Stateless service — instantiate, call, discard."""

    def __init__(self, pixel_id, access_token):
        if not pixel_id or not access_token:
            raise ValueError("Both pixel_id and access_token are required for Meta CAPI")
        self.pixel_id = str(pixel_id).strip()
        self.access_token = str(access_token).strip()
        self.endpoint = f"{META_GRAPH_BASE_URL}/{self.pixel_id}/events"

    # ------------------------------------------------------------------
    # Low-level sender
    # ------------------------------------------------------------------

    def _send_events(self, events, test_event_code=None):
        """
        POST one or more events to the Conversions API.

        Args:
            events: list of event dicts (each following Meta's schema)
            test_event_code: optional test code from Events Manager

        Returns:
            dict with 'success' (bool), 'response' or 'error'
        """
        payload = {
            "data": json.dumps(events),
            "access_token": self.access_token,
        }
        if test_event_code:
            payload["test_event_code"] = test_event_code

        try:
            resp = requests.post(self.endpoint, data=payload, timeout=15)
            result = resp.json()

            if resp.status_code == 200:
                _logger.info(
                    "Meta CAPI event(s) sent successfully to pixel %s: %s",
                    self.pixel_id,
                    result,
                )
                return {"success": True, "response": result}
            else:
                _logger.error(
                    "Meta CAPI error %s for pixel %s: %s",
                    resp.status_code,
                    self.pixel_id,
                    result,
                )
                return {"success": False, "error": result}

        except requests.Timeout:
            _logger.error("Meta CAPI request timed out for pixel %s", self.pixel_id)
            return {"success": False, "error": "Request timed out"}
        except Exception as exc:
            _logger.error("Meta CAPI exception for pixel %s: %s", self.pixel_id, exc)
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Build user_data dict (hashed PII)
    # ------------------------------------------------------------------

    def _build_user_data(self, lead):
        """
        Build the ``user_data`` block from an Odoo ``crm.lead`` record.

        All fields that Meta can match on are included when available.
        PII values are SHA-256 hashed as arrays per Meta's CAPI v24 spec.
        """
        first_name, last_name = _split_name(
            lead.contact_name or lead.partner_name or lead.name
        )

        user_data = {}

        # --- Hashed PII (formatted as arrays per Meta spec) ---
        em = _hash_value(lead.email_from)
        if em:
            user_data["em"] = [em]

        ph = _hash_phone(lead.phone or lead.mobile)
        if ph:
            user_data["ph"] = [ph]

        fn = _hash_value(first_name)
        if fn:
            user_data["fn"] = [fn]

        ln = _hash_value(last_name)
        if ln:
            user_data["ln"] = [ln]

        city_val = lead.city or "Istanbul"
        ct = _hash_value(city_val)
        if ct:
            user_data["ct"] = [ct]

        state_val = lead.state_id.name if lead.state_id else city_val
        st = _hash_value(state_val)
        if st:
            user_data["st"] = [st]

        zp = _hash_value(lead.zip)
        if zp:
            user_data["zp"] = [zp]

        country_code = lead.country_id.code.lower() if lead.country_id and lead.country_id.code else "tr"
        co = _hash_value(country_code)
        if co:
            user_data["country"] = [co]

        # --- Non-hashed identifiers & External ID ---
        if lead.id:
            user_data["external_id"] = [str(lead.id), _hash_value(str(lead.id))]

        # fbc / fbp cookies — stored on lead if captured from website form
        fbc = getattr(lead, "meta_fbc", None)
        if fbc:
            user_data["fbc"] = fbc

        fbp = getattr(lead, "meta_fbp", None)
        if fbp:
            user_data["fbp"] = fbp

        # Client IP and User Agent — captured from webhook request
        client_ip = getattr(lead, "meta_client_ip", None)
        if client_ip:
            user_data["client_ip_address"] = client_ip

        client_ua = getattr(lead, "meta_client_user_agent", None)
        if client_ua:
            user_data["client_user_agent"] = client_ua

        return user_data

    # ------------------------------------------------------------------
    # Build custom_data dict
    # ------------------------------------------------------------------

    def _build_custom_data(self, lead, event_name, **extra):
        """Build ``custom_data`` block with lead metadata."""
        custom = {
            "lead_id": str(lead.id) if lead.id else None,
            "content_category": "lead",
            "content_name": lead.name or "",
            "status": lead.stage_id.name if lead.stage_id else "",
        }

        # Add campaign info if available
        if hasattr(lead, "meta_campaign_id") and lead.meta_campaign_id:
            custom["campaign_id"] = lead.meta_campaign_id
        if hasattr(lead, "meta_campaign_name") and lead.meta_campaign_name:
            custom["campaign_name"] = lead.meta_campaign_name
        if hasattr(lead, "meta_adset_id") and lead.meta_adset_id:
            custom["adset_id"] = lead.meta_adset_id
        if hasattr(lead, "meta_ad_id") and lead.meta_ad_id:
            custom["ad_id"] = lead.meta_ad_id
        if hasattr(lead, "meta_form_id") and lead.meta_form_id:
            custom["form_id"] = lead.meta_form_id

        # Content type
        custom["content_type"] = "product"

        # Currency — default TRY for Turkish market
        custom["currency"] = extra.get("currency", "TRY")

        # Value — for Purchase events
        if event_name == "Purchase" and lead.expected_revenue:
            custom["value"] = float(lead.expected_revenue)
        elif event_name == "Purchase":
            custom["value"] = 0.0

        # Merge any extra fields
        custom.update({k: v for k, v in extra.items() if k != "currency"})

        # Remove None values
        return {k: v for k, v in custom.items() if v is not None}

    # ------------------------------------------------------------------
    # High-level event builders
    # ------------------------------------------------------------------

    def _build_event(self, lead, event_name, event_source_url=None, **extra):
        """
        Build a single event dict conforming to Meta CAPI schema.

        Reference: https://developers.facebook.com/docs/marketing-api/conversions-api/parameters
        """
        # Unique event ID for deduplication
        event_id = f"{event_name.lower()}_{lead.id}_{int(time.time())}"

        event = {
            "event_name": event_name,
            "event_time": int(time.time()),
            "event_id": event_id,
            "event_source_url": event_source_url or "https://akod.tech",
            "action_source": "system_generated",
            "user_data": self._build_user_data(lead),
            "custom_data": self._build_custom_data(lead, event_name, **extra),
        }

        # opt_out — default to not opting out
        event["opt_out"] = False

        # data_processing_options — empty = no LDU restrictions
        event["data_processing_options"] = []

        return event

    def send_lead_event(self, lead, event_source_url=None, test_event_code=None):
        """
        Fire a **Lead** event to Meta CAPI.

        Triggered when a lead reaches a "qualified" stage.
        """
        event = self._build_event(
            lead,
            "Lead",
            event_source_url=event_source_url,
        )
        _logger.info(
            "Sending Lead event for CRM lead %s (meta_leadgen_id=%s) to pixel %s",
            lead.id,
            getattr(lead, "meta_leadgen_id", "N/A"),
            self.pixel_id,
        )
        return self._send_events([event], test_event_code=test_event_code)

    def send_purchase_event(self, lead, value=None, currency="TRY",
                            event_source_url=None, test_event_code=None):
        """
        Fire a **Purchase** event to Meta CAPI.

        Triggered when a lead is marked as sold / satisfied (closed-won).
        """
        extra = {}
        if value is not None:
            extra["value"] = float(value)
        if currency:
            extra["currency"] = currency

        event = self._build_event(
            lead,
            "Purchase",
            event_source_url=event_source_url,
            **extra,
        )
        _logger.info(
            "Sending Purchase event for CRM lead %s (meta_leadgen_id=%s) to pixel %s",
            lead.id,
            getattr(lead, "meta_leadgen_id", "N/A"),
            self.pixel_id,
        )
        return self._send_events([event], test_event_code=test_event_code)

    def send_custom_event(self, lead, event_name, event_source_url=None,
                          test_event_code=None, **extra):
        """
        Fire any custom event to Meta CAPI.

        Useful for future extensions (e.g., "Schedule", "Contact", etc.).
        """
        event = self._build_event(
            lead,
            event_name,
            event_source_url=event_source_url,
            **extra,
        )
        _logger.info(
            "Sending %s event for CRM lead %s to pixel %s",
            event_name,
            lead.id,
            self.pixel_id,
        )
        return self._send_events([event], test_event_code=test_event_code)

    # ------------------------------------------------------------------
    # Pixel verification helper
    # ------------------------------------------------------------------

    @staticmethod
    def verify_pixel(pixel_id, access_token):
        """
        Call the Graph API to verify the pixel ID is valid and accessible.

        Returns dict with pixel info or error.
        """
        url = f"{META_GRAPH_BASE_URL}/{pixel_id}"
        params = {
            "access_token": access_token,
            "fields": "id,name,is_unavailable,data_use_setting,automatic_matching_fields",
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                _logger.info("Meta Pixel verified: %s (%s)", data.get("name"), data.get("id"))
                return {"success": True, "pixel": data}
            else:
                err = resp.json()
                _logger.error("Meta Pixel verification failed: %s", err)
                return {"success": False, "error": err}
        except Exception as exc:
            _logger.error("Meta Pixel verification exception: %s", exc)
            return {"success": False, "error": str(exc)}
