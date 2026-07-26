# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Normalize market listing values (currency, units, location text, numbers)."""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

_NUM_RE = re.compile(r"[^\d.,\-]")


def parse_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    # TR format: 1.250.000,50 → 1250000.50
    cleaned = _NUM_RE.sub("", text)
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        cleaned = cleaned.replace(",", ".") if len(parts[-1]) <= 2 else cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_currency(code: Any, default: str = "TRY") -> str:
    if not code:
        return default
    text = str(code).strip().upper()
    aliases = {
        "TL": "TRY",
        "₺": "TRY",
        "TURKISH LIRA": "TRY",
        "$": "USD",
        "US$": "USD",
        "€": "EUR",
        "EURO": "EUR",
    }
    return aliases.get(text, text[:3] if len(text) >= 3 else default)


def normalize_transaction(value: Any) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip().lower()
    mapping = {
        "sale": "sale",
        "satilik": "sale",
        "satılık": "sale",
        "sell": "sale",
        "rent": "rent",
        "kiralik": "rent",
        "kiralık": "rent",
        "for rent": "rent",
        "short_term": "short_term_rent",
        "short-term": "short_term_rent",
        "günlük": "short_term_rent",
        "gunluk": "short_term_rent",
    }
    return mapping.get(text, text if text in ("sale", "rent", "short_term_rent") else None)


def price_per_m2(asking_price: Optional[float], area: Optional[float]) -> Optional[float]:
    if asking_price is None or area is None or area <= 0:
        return None
    return round(asking_price / area, 2)


def normalize_raw_row(raw: Dict[str, Any], mapping_get=None) -> Tuple[Dict[str, Any], list]:
    """Return (normalized_vals, warnings)."""
    warnings = []
    get = raw.get

    def pick(*keys, default=None):
        for k in keys:
            if k in raw and raw[k] not in (None, ""):
                return raw[k]
        return default

    external_id = pick("external_id", "external_listing_id", "id", "listing_id")
    if not external_id:
        warnings.append("missing_external_id")

    tx = normalize_transaction(pick("transaction_type", "transaction", "ilan_tipi"))
    if not tx:
        warnings.append("unmapped_transaction")
        tx = "sale"

    currency = normalize_currency(pick("currency", "para_birimi"))
    asking = parse_number(pick("asking_price", "price", "fiyat"))
    gross = parse_number(pick("gross_area", "gross_m2", "brut_m2", "m2"))
    net = parse_number(pick("net_area", "net_m2", "net_metrekare"))

    category = pick("category", "category_code", "kategori")
    if mapping_get and category:
        mapped = mapping_get("category", category)
        if mapped:
            category = mapped
        else:
            warnings.append("unmapped_category:%s" % category)

    province = pick("province", "city", "il", "sehir")
    district = pick("district", "ilce")
    neighborhood = pick("neighborhood", "mahalle")

    vals = {
        "external_listing_id": str(external_id) if external_id else False,
        "transaction_type": tx,
        "category_code": str(category or "unknown"),
        "subcategory_code": str(pick("subcategory", "alt_kategori") or ""),
        "title": (str(pick("title", "baslik") or "")[:200] or False),
        "province": str(province or ""),
        "district": str(district or ""),
        "neighborhood": str(neighborhood or ""),
        "source_location_text": str(pick("location_text", "adres") or ""),
        "latitude": parse_number(pick("latitude", "lat")),
        "longitude": parse_number(pick("longitude", "lng", "lon")),
        "currency_name": currency,
        "asking_price": asking or 0.0,
        "gross_area": gross,
        "net_area": net,
        "gross_price_m2": price_per_m2(asking, gross),
        "net_price_m2": price_per_m2(asking, net),
        "rooms": str(pick("rooms", "oda") or ""),
        "bedrooms": parse_number(pick("bedrooms", "yatak_odasi")),
        "bathrooms": parse_number(pick("bathrooms", "banyo")),
        "building_age": str(pick("building_age", "bina_yasi") or ""),
        "floor": str(pick("floor", "kat") or ""),
        "total_floors": str(pick("total_floors", "kat_sayisi") or ""),
        "heating": str(pick("heating", "isitma") or ""),
        "kitchen": str(pick("kitchen", "mutfak") or ""),
        "balcony": bool(pick("balcony", "balkon")) if pick("balcony", "balkon") is not None else False,
        "elevator": bool(pick("elevator", "asansor", "asansör")) if pick("elevator", "asansor", "asansör") is not None else False,
        "parking": str(pick("parking", "otopark") or ""),
        "furnished": str(pick("furnished", "esya") or ""),
        "use_status": str(pick("use_status", "kullanim") or ""),
        "in_compound": bool(pick("in_compound", "site")) if pick("in_compound", "site") is not None else False,
        "mortgage_eligible": bool(pick("mortgage_eligible", "krediye_uygun")) if pick("mortgage_eligible", "krediye_uygun") is not None else False,
        "title_deed_status": str(pick("title_deed_status", "tapu") or ""),
        "exchange_possible": bool(pick("exchange_possible", "takas")) if pick("exchange_possible", "takas") is not None else False,
        "seller_type": str(pick("seller_type", "kimden") or "unknown"),
        "organization_name": str(pick("organization_name", "emlak_ofisi") or ""),
        "seller_external_id": str(pick("seller_external_id", "seller_id") or ""),
        "permitted_source_url": str(pick("permitted_source_url", "url", "source_url") or ""),
        "media_count": int(parse_number(pick("media_count")) or 0),
        "source_listing_date": pick("source_listing_date", "listing_date", "ilan_tarihi"),
        "image_urls": pick("image_urls", "images") or [],
        "raw_payload": raw,
    }
    if asking is None:
        warnings.append("missing_asking_price")
    if not province:
        warnings.append("missing_location")
    return vals, warnings
