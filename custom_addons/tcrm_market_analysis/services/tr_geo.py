# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Turkey İl / İlçe / Semt-Mahalle taxonomy for searchable cascading filters."""
from __future__ import annotations

import json
import os
import unicodedata
from functools import lru_cache
from typing import Dict, List, Optional


def _data_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tr_geo.json")


@lru_cache(maxsize=1)
def load_geo() -> dict:
    with open(_data_path(), encoding="utf-8") as fh:
        return json.load(fh)


def fold(text: str) -> str:
    """Case/diacritic-insensitive fold for Turkish place names."""
    if not text:
        return ""
    # Turkish-specific mappings before NFKD
    table = str.maketrans({
        "İ": "i", "I": "i", "ı": "i",
        "Ş": "s", "ş": "s",
        "Ğ": "g", "ğ": "g",
        "Ü": "u", "ü": "u",
        "Ö": "o", "ö": "o",
        "Ç": "c", "ç": "c",
    })
    text = text.translate(table)
    norm = unicodedata.normalize("NFKD", text)
    return "".join(c for c in norm if not unicodedata.combining(c)).lower().strip()


def slugify(text: str) -> str:
    return fold(text).replace(" ", "-")


def suggest_provinces(query: str = "", limit: int = 20) -> List[dict]:
    q = fold(query)
    out = []
    for p in load_geo()["provinces"]:
        if not q or q in fold(p["name"]) or q in p["slug"]:
            out.append({"name": p["name"], "slug": p["slug"]})
        if len(out) >= limit:
            break
    return out


def resolve_province(name_or_slug: str) -> Optional[dict]:
    if not name_or_slug:
        return None
    key = fold(name_or_slug)
    for p in load_geo()["provinces"]:
        if fold(p["name"]) == key or p["slug"] == key or p["slug"] == slugify(name_or_slug):
            return p
    # prefix / contains
    for p in load_geo()["provinces"]:
        if key in fold(p["name"]) or key in p["slug"]:
            return p
    return None


def suggest_districts(province: str, query: str = "", limit: int = 40) -> List[dict]:
    prov = resolve_province(province)
    if not prov:
        return []
    districts = load_geo().get("districts", {}).get(prov["slug"], [])
    q = fold(query)
    out = []
    for d in districts:
        if not q or q in fold(d["name"]) or q in d["slug"]:
            out.append({"name": d["name"], "slug": d["slug"], "province": prov["name"], "province_slug": prov["slug"]})
        if len(out) >= limit:
            break
    return out


def resolve_district(province: str, name_or_slug: str) -> Optional[dict]:
    if not name_or_slug:
        return None
    items = suggest_districts(province, query="", limit=500)
    key = fold(name_or_slug)
    for d in items:
        if fold(d["name"]) == key or d["slug"] == key or d["slug"] == slugify(name_or_slug):
            return d
    for d in items:
        if key in fold(d["name"]) or key in d["slug"]:
            return d
    return None


def suggest_neighborhoods(province: str, district: str, query: str = "", limit: int = 40) -> List[dict]:
    prov = resolve_province(province)
    dist = resolve_district(province, district) if province and district else None
    if not prov or not dist:
        return []
    key = "%s/%s" % (prov["slug"], dist["slug"])
    neighborhoods = load_geo().get("neighborhoods", {}).get(key, [])
    q = fold(query)
    out = []
    for n in neighborhoods:
        if not q or q in fold(n["name"]) or q in n["slug"]:
            out.append({
                "name": n["name"],
                "slug": n["slug"],
                "province": prov["name"],
                "district": dist["name"],
            })
        if len(out) >= limit:
            break
    return out


def build_filter_slugs(province: str = "", district: str = "", neighborhood: str = "") -> Dict[str, str]:
    """Resolve human names to URL slugs without requiring internal IDs."""
    result = {"province_slug": "", "district_slug": "", "neighborhood_slug": "",
              "province_name": "", "district_name": "", "neighborhood_name": ""}
    prov = resolve_province(province) if province else None
    if prov:
        result["province_slug"] = prov["slug"]
        result["province_name"] = prov["name"]
    dist = resolve_district(province, district) if province and district else None
    if dist:
        result["district_slug"] = dist["slug"]
        result["district_name"] = dist["name"]
    if province and district and neighborhood:
        for n in suggest_neighborhoods(province, district, query="", limit=500):
            if fold(n["name"]) == fold(neighborhood) or n["slug"] == slugify(neighborhood):
                result["neighborhood_slug"] = n["slug"]
                result["neighborhood_name"] = n["name"]
                break
        if not result["neighborhood_slug"] and neighborhood:
            result["neighborhood_slug"] = slugify(neighborhood)
            result["neighborhood_name"] = neighborhood
    return result
