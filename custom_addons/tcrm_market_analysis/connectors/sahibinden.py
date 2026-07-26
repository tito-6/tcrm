# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Public Sahibinden listing collector (no login).

Rules:
- Only fetch publicly accessible pages without authentication.
- Do NOT bypass CAPTCHA, login walls, access controls, or anti-bot protection.
- Do NOT use rotating proxies, fingerprint spoofing, or stealth automation.
- If the site blocks the request, stop and surface the exact error.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from .base import (
    AuthorizationError,
    BaseMarketConnector,
    ConnectorError,
    FetchPageResult,
    PermanentFailure,
    RateLimitError,
)
from .registry import register
from ..services.tr_geo import build_filter_slugs, slugify

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None


CATEGORY_SLUGS = {
    "daire": "daire",
    "apartment": "daire",
    "residential": "daire",
    "rezidans": "residence",
    "residence": "residence",
    "villa": "villa",
    "mustakil": "mustakil-ev",
    "mustakil_ev": "mustakil-ev",
    "müstakil ev": "mustakil-ev",
    "isyeri": "isyerleri",
    "işyeri": "isyerleri",
    "commercial": "isyerleri",
    "arsa": "arsa",
    "land": "arsa",
}

TRANSACTION_PREFIX = {
    "sale": "satilik",
    "satilik": "satilik",
    "satılık": "satilik",
    "rent": "kiralik",
    "kiralik": "kiralik",
    "kiralık": "kiralik",
}


class BlockedError(PermanentFailure):
    """Site blocked the request (CAPTCHA / anti-bot / access control)."""


@register
class SahibindenConnector(BaseMarketConnector):
    source_type = "sahibinden"
    display_name = "Sahibinden (Public)"

    BASE = "https://www.sahibinden.com"
    DEFAULT_CAPABILITIES = {
        **BaseMarketConnector.DEFAULT_CAPABILITIES,
        "listing_search": True,
        "details": True,
        "pagination": True,
        "seller_type": True,
        "coordinates": False,
        "images": True,
        "removed_detection": True,
        "taxonomy": True,
    }

    # Default identifiable client. When the user pastes their own Cookie/UA from
    # DevTools, those values are used instead — we never harvest the OS browser profile
    # and never solve Cloudflare/CAPTCHA challenges.
    USER_AGENT = "TCRM-MarketAnalysis/1.0 (+https://tcrm.local; public-listing-collector)"

    def __init__(self, env, source):
        super().__init__(env, source)
        self._session = None
        self._http_get = None  # injectable for tests

    def validate_configuration(self):
        self.assert_enabled()
        if requests is None or BeautifulSoup is None:
            raise ConnectorError(
                "Python packages 'requests' and 'beautifulsoup4' are required for Sahibinden public collection."
            )
        mode = "user_cookie_session" if (self.source.browser_cookie or "").strip() else "public_no_login"
        return {"ok": True, "source_type": self.source_type, "mode": mode}

    def assert_authorized(self):
        # Public collector does not require licensed API credentials.
        # Still requires explicit enable + non-kill-switch.
        if self.source.authorization_state == "revoked":
            raise AuthorizationError("Sahibinden source authorization was revoked.")
        if self.source.kill_switch:
            raise ConnectorError("Kill switch is active.")

    def test_connection(self):
        self.validate_configuration()
        self.assert_authorized()
        # Lightweight public HEAD/GET of homepage — stop on block.
        status, body, final_url = self._http_fetch(self.BASE + "/")
        self._raise_if_blocked(status, body, final_url, allow_empty=True)
        return {"ok": True, "message": "Public endpoint reachable (HTTP %s)." % status}

    # --- URL building -------------------------------------------------------

    def build_search_url(
        self,
        *,
        transaction_type: str = "sale",
        category: str = "daire",
        province: str = "",
        district: str = "",
        neighborhood: str = "",
        page: int = 1,
    ) -> str:
        tx = TRANSACTION_PREFIX.get((transaction_type or "sale").lower(), "satilik")
        cat = CATEGORY_SLUGS.get((category or "daire").lower(), slugify(category or "daire"))
        path = "/%s-%s" % (tx, cat)
        slugs = build_filter_slugs(province, district, neighborhood)
        if slugs["province_slug"]:
            path += "/" + slugs["province_slug"]
        if slugs["district_slug"]:
            path += "/" + slugs["district_slug"]
        if slugs["neighborhood_slug"]:
            path += "/" + slugs["neighborhood_slug"]
        if page and int(page) > 1:
            path += "?pagingOffset=%s" % ((int(page) - 1) * 20)
        return urljoin(self.BASE, path)

    # --- HTTP ---------------------------------------------------------------

    def _parsed_browser_session(self) -> Dict[str, str]:
        """Build request headers from admin-pasted Cookie / User-Agent / DevTools dump.

        Accepts either a bare Cookie value, or a full Request Headers paste
        (Cookie / User-Agent / Accept-Language / sec-ch-ua* lines).
        Never reads the OS browser profile.
        """
        raw_cookie = (self.source.browser_cookie or "").strip()
        raw_ua = (self.source.browser_user_agent or "").strip()
        parsed = parse_devtools_headers(raw_cookie)
        looks_like_dump = bool(parsed.get("cookie") or parsed.get("user-agent"))
        if looks_like_dump:
            cookie = parsed.get("cookie") or ""
            ua = raw_ua or parsed.get("user-agent") or self.USER_AGENT
        else:
            cookie = raw_cookie
            if cookie.lower().startswith("cookie:"):
                cookie = cookie.split(":", 1)[1].strip()
            ua = raw_ua or self.USER_AGENT

        headers = browser_headers_for_ua(ua)
        # Prefer explicit values from a full DevTools paste when present.
        for key in (
            "accept",
            "accept-language",
            "sec-ch-ua",
            "sec-ch-ua-mobile",
            "sec-ch-ua-platform",
            "referer",
        ):
            if parsed.get(key):
                headers[header_case(key)] = parsed[key]
        if cookie:
            headers["Cookie"] = cookie
        headers["User-Agent"] = ua
        headers["Referer"] = headers.get("Referer") or (self.BASE + "/")
        return headers

    def _get_session(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(self._parsed_browser_session())
        return self._session

    def _http_fetch(self, url: str, *, allow_empty: bool = False):
        if self._http_get:
            return self._http_get(url)
        # Polite single-thread delay; not a bypass mechanism.
        delay = max(1.0, 60.0 / max(1, self.source.rate_limit_per_minute or 10))
        time.sleep(min(delay, 5.0))
        try:
            session = self._get_session()
            # Document navigation hints (same origin after homepage referer).
            resp = session.get(
                url,
                timeout=30,
                allow_redirects=True,
                headers={
                    "Sec-Fetch-Site": "same-origin" if urlstartswith_host(url, self.BASE) else "none",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-User": "?1",
                    "Sec-Fetch-Dest": "document",
                    "Upgrade-Insecure-Requests": "1",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                },
            )
        except requests.RequestException as exc:
            raise ConnectorError("Network error fetching %s: %s" % (url, exc)) from exc
        return resp.status_code, resp.text or "", resp.url

    def _raise_if_blocked(self, status: int, body: str, url: str, *, allow_empty: bool = False):
        text = (body or "").lower()
        markers = [
            "captcha",
            "recaptcha",
            "g-recaptcha",
            "cf-browser-verification",
            "cloudflare",
            "access denied",
            "erişim engellendi",
            "unusual traffic",
            "bot detection",
            "challenge-platform",
            "just a moment",
        ]
        has_cookie = bool((self.source.browser_cookie or "").strip())
        if status in (401, 403) or "just a moment" in text:
            if not has_cookie:
                hint = (
                    "Paste a fresh Cookie + User-Agent (or the full Request Headers block) "
                    "from your browser DevTools after YOU open https://www.sahibinden.com/satilik-daire "
                    "successfully (HTTP 200). Use the same machine/IP that runs TCRM — "
                    "cf_clearance is IP-bound. "
                )
            else:
                hint = (
                    "Pasted session was rejected. Refresh Cookie + User-Agent from a NEW "
                    "successful document request to /satilik-daire (not only the homepage), "
                    "paste both into the Sahibinden source (same UA that created cf_clearance), "
                    "and ensure TCRM runs from the same public IP as that browser. "
                    "Cookies expire quickly (often minutes). "
                )
            raise BlockedError(
                "Blocked by Cloudflare/anti-bot while fetching %s (HTTP %s). "
                "Challenge/CAPTCHA bypass is not implemented. %s"
                "Exact status: %s"
                % (url, status, hint, status)
            )
        if status == 429:
            raise RateLimitError(
                "Rate limited by sahibinden.com while fetching %s (HTTP 429). Job stopped."
                % url
            )
        if status >= 500:
            raise ConnectorError("Server error from sahibinden.com (HTTP %s) at %s" % (status, url))
        if any(m in text for m in markers):
            raise BlockedError(
                "Anti-bot / CAPTCHA / challenge page detected at %s (HTTP %s). "
                "Collection stopped without bypass. Response markers matched."
                % (url, status)
            )
        if status == 200 and not allow_empty and len(body or "") < 200:
            raise BlockedError(
                "Suspiciously empty response from %s (HTTP %s, %s bytes). Job stopped."
                % (url, status, len(body or ""))
            )

    # --- parsing ------------------------------------------------------------

    def parse_search_html(self, html: str, page_url: str) -> List[Dict[str, Any]]:
        if BeautifulSoup is None:
            raise ConnectorError("beautifulsoup4 is required")
        soup = BeautifulSoup(html, "html.parser")
        rows: List[Dict[str, Any]] = []

        # Classic search result rows
        for tr in soup.select("tr.searchResultsItem, tr[data-id]"):
            rec = self._parse_result_row(tr, page_url)
            if rec:
                rows.append(rec)

        # Card / classified tiles
        if not rows:
            for card in soup.select("div.classified-list-item, li.searchResultsItem, div[data-classified-id]"):
                rec = self._parse_result_row(card, page_url)
                if rec:
                    rows.append(rec)

        # JSON-LD ItemList fallback
        if not rows:
            for script in soup.select('script[type="application/ld+json"]'):
                try:
                    data = json.loads(script.string or "")
                except Exception:
                    continue
                rows.extend(self._parse_jsonld(data, page_url))

        return rows

    def _parse_result_row(self, node, page_url: str) -> Optional[Dict[str, Any]]:
        ext_id = (
            node.get("data-id")
            or node.get("data-classified-id")
            or node.get("data-content")
        )
        link = node.select_one("a.classifiedTitle, a[href*='/ilan/'], a[href*='-detay']")
        href = link.get("href") if link else None
        title = (link.get_text(" ", strip=True) if link else "") or ""
        if href and href.startswith("/"):
            href = urljoin(self.BASE, href)
        if not ext_id and href:
            m = re.search(r"-(\d+)(?:\?|$)", href)
            if m:
                ext_id = m.group(1)
        if not ext_id and not href:
            return None

        price_el = node.select_one(".searchResultsPriceValue, .classified-price-container, span.price")
        price_text = price_el.get_text(" ", strip=True) if price_el else ""
        asking, currency = self._parse_price(price_text)

        attrs = [a.get_text(" ", strip=True) for a in node.select(
            "td.searchResultsAttributeValue, span.tag, li.attribute"
        )]
        location_el = node.select_one(".searchResultsLocationValue, .classified-location, td.searchResultsLocationValue")
        location_text = location_el.get_text(" ", strip=True) if location_el else ""
        loc_parts = [p.strip() for p in re.split(r"[/\n|]", location_text) if p.strip()]

        img = node.select_one("img")
        img_url = ""
        if img:
            img_url = img.get("data-src") or img.get("src") or ""
            if img_url.startswith("//"):
                img_url = "https:" + img_url

        date_el = node.select_one(".searchResultsDateValue, time, span.date")
        listing_date = date_el.get_text(" ", strip=True) if date_el else ""

        return {
            "external_id": str(ext_id),
            "title": title[:200],
            "permitted_source_url": href or "",
            "url": href or "",
            "asking_price": asking,
            "price": asking,
            "currency": currency,
            "province": loc_parts[0] if len(loc_parts) > 0 else "",
            "district": loc_parts[1] if len(loc_parts) > 1 else "",
            "neighborhood": loc_parts[2] if len(loc_parts) > 2 else "",
            "location_text": location_text,
            "rooms": self._pick_attr(attrs, r"\d+\s*\+\s*\d+"),
            "gross_m2": self._pick_number(attrs, r"(\d+(?:[.,]\d+)?)\s*m"),
            "building_age": self._pick_attr(attrs, r"Yaş|yas|Age"),
            "floor": self._pick_attr(attrs, r"Kat"),
            "image_urls": [img_url] if img_url and not img_url.startswith("data:") else [],
            "media_count": 1 if img_url else 0,
            "source_listing_date": listing_date or False,
            "seller_type": "unknown",
        }

    def _parse_jsonld(self, data, page_url: str) -> List[dict]:
        rows = []
        items = []
        if isinstance(data, dict) and data.get("@type") == "ItemList":
            items = data.get("itemListElement") or []
        elif isinstance(data, list):
            for block in data:
                if isinstance(block, dict) and block.get("@type") == "ItemList":
                    items.extend(block.get("itemListElement") or [])
        for el in items:
            item = el.get("item") if isinstance(el, dict) else None
            if not isinstance(item, dict):
                continue
            url = item.get("url") or ""
            ext = ""
            m = re.search(r"-(\d+)(?:\?|$)", url or "")
            if m:
                ext = m.group(1)
            offers = item.get("offers") or {}
            price = offers.get("price") if isinstance(offers, dict) else None
            rows.append({
                "external_id": ext or url,
                "title": item.get("name") or "",
                "permitted_source_url": url,
                "url": url,
                "asking_price": float(price) if price else 0,
                "currency": (offers.get("priceCurrency") if isinstance(offers, dict) else None) or "TRY",
                "image_urls": [item["image"]] if item.get("image") else [],
            })
        return rows

    @staticmethod
    def _parse_price(text: str):
        if not text:
            return 0.0, "TRY"
        currency = "TRY"
        up = text.upper()
        if "USD" in up or "$" in text:
            currency = "USD"
        elif "EUR" in up or "€" in text:
            currency = "EUR"
        digits = re.sub(r"[^\d]", "", text.split(",")[0])
        try:
            return float(digits) if digits else 0.0, currency
        except ValueError:
            return 0.0, currency

    @staticmethod
    def _pick_attr(attrs: List[str], pattern: str) -> str:
        rx = re.compile(pattern, re.I)
        for a in attrs:
            if rx.search(a):
                return a
        return ""

    @staticmethod
    def _pick_number(attrs: List[str], pattern: str):
        rx = re.compile(pattern, re.I)
        for a in attrs:
            m = rx.search(a.replace(".", "").replace(",", "."))
            if m:
                try:
                    return float(m.group(1).replace(",", "."))
                except ValueError:
                    return False
        return False

    def parse_detail_html(self, html: str, page_url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        info = {}
        for li in soup.select("ul.classifiedInfoList li, ul#classifiedProperties li, div.classified-info li"):
            label = li.select_one("strong, span")
            if not label:
                continue
            key = label.get_text(" ", strip=True).rstrip(":")
            val = li.get_text(" ", strip=True).replace(key, "", 1).strip(" :")
            info[key] = val

        def g(*names):
            for n in names:
                for k, v in info.items():
                    if fold_key(k) == fold_key(n) or fold_key(n) in fold_key(k):
                        return v
            return ""

        images = []
        for img in soup.select("div#gallery img, div.classifiedDetailGallery img, img.s-image"):
            src = img.get("data-src") or img.get("src") or ""
            if src.startswith("//"):
                src = "https:" + src
            if src and not src.startswith("data:") and src not in images:
                images.append(src)

        return {
            "rooms": g("Oda Sayısı", "Room"),
            "gross_m2": _to_float(g("m² (Brüt)", "Brüt", "Gross")),
            "net_m2": _to_float(g("m² (Net)", "Net")),
            "building_age": g("Bina Yaşı", "Building Age"),
            "floor": g("Bulunduğu Kat", "Floor"),
            "total_floors": g("Kat Sayısı", "Number of Floors"),
            "heating": g("Isıtma", "Heating"),
            "bathrooms": _to_float(g("Banyo Sayısı", "Bathroom")),
            "kitchen": g("Mutfak", "Kitchen"),
            "balcony": _to_bool(g("Balkon", "Balcony")),
            "elevator": _to_bool(g("Asansör", "Elevator")),
            "parking": g("Otopark", "Parking"),
            "furnished": g("Eşyalı", "Furnished"),
            "use_status": g("Kullanım Durumu", "Usage"),
            "in_compound": _to_bool(g("Site İçerisinde", "Site")),
            "mortgage_eligible": _to_bool(g("Krediye Uygun", "Mortgage")),
            "title_deed_status": g("Tapu Durumu", "Title Deed"),
            "seller_type": g("Kimden", "From"),
            "image_urls": images,
            "media_count": len(images),
            "permitted_source_url": page_url,
        }

    # --- fetch API ----------------------------------------------------------

    def fetch_page(self, cursor: Optional[str] = None, **kwargs) -> FetchPageResult:
        self.assert_enabled()
        self.assert_authorized()
        page = int(cursor or kwargs.get("page") or 1)
        url = kwargs.get("url") or self.build_search_url(
            transaction_type=kwargs.get("transaction_type") or self.source.filter_transaction or "sale",
            category=kwargs.get("category") or self.source.filter_category or "daire",
            province=kwargs.get("province") or self.source.filter_province or "",
            district=kwargs.get("district") or self.source.filter_district or "",
            neighborhood=kwargs.get("neighborhood") or self.source.filter_neighborhood or "",
            page=page,
        )
        status, body, final_url = self._http_fetch(url)
        self._raise_if_blocked(status, body, final_url)
        records = self.parse_search_html(body, final_url)
        tx = kwargs.get("transaction_type") or self.source.filter_transaction or "sale"
        cat = kwargs.get("category") or self.source.filter_category or "daire"
        for rec in records:
            rec.setdefault("transaction_type", "sale" if "satilik" in (tx or "") or tx == "sale" else "rent")
            if tx in ("sale", "satilik", "satılık"):
                rec["transaction_type"] = "sale"
            elif tx in ("rent", "kiralik", "kiralık"):
                rec["transaction_type"] = "rent"
            rec.setdefault("category", cat if cat not in ("daire", "apartment") else "residential")
            if cat in ("daire", "apartment", "residential"):
                rec["category"] = "residential"
                rec["subcategory"] = "apartment"
            elif cat in ("rezidans", "residence"):
                rec["category"] = "residential"
                rec["subcategory"] = "residence"
            elif cat == "villa":
                rec["category"] = "residential"
                rec["subcategory"] = "villa"
            elif "mustakil" in (cat or "") or "müstakil" in (cat or ""):
                rec["category"] = "residential"
                rec["subcategory"] = "detached"
            elif "isyeri" in (cat or "") or "işyeri" in (cat or "") or cat == "commercial":
                rec["category"] = "commercial"
                rec["subcategory"] = "workplace"
            elif cat in ("arsa", "land"):
                rec["category"] = "land"
                rec["subcategory"] = "land"
        next_cursor = str(page + 1) if records else None
        return FetchPageResult(records=records, next_cursor=next_cursor, exhausted=not bool(records))

    def fetch_detail(self, external_id: str, url: Optional[str] = None) -> Dict[str, Any]:
        self.assert_enabled()
        self.assert_authorized()
        if not url:
            raise ConnectorError("Detail URL required for public collector.")
        status, body, final_url = self._http_fetch(url)
        self._raise_if_blocked(status, body, final_url)
        detail = self.parse_detail_html(body, final_url)
        detail["external_id"] = str(external_id)
        return detail

    def collect(
        self,
        *,
        max_pages: Optional[int] = None,
        max_records: Optional[int] = None,
        fetch_details: bool = False,
        progress_callback=None,
    ) -> List[Dict[str, Any]]:
        """Collect public listings; stop immediately on block/rate-limit."""
        self.validate_configuration()
        self.assert_authorized()
        max_pages = max_pages or self.source.max_pages or 5
        max_records = max_records or self.source.max_records or 100
        all_rows: List[Dict[str, Any]] = []
        cursor = "1"
        pages = 0
        while pages < max_pages and len(all_rows) < max_records:
            if self._kill_switch or self.source.kill_switch:
                raise ConnectorError("Kill switch engaged.")
            page = self.fetch_page(cursor=cursor)
            pages += 1
            for raw in page.records:
                if fetch_details and raw.get("permitted_source_url"):
                    try:
                        detail = self.fetch_detail(raw["external_id"], url=raw["permitted_source_url"])
                        raw.update({k: v for k, v in detail.items() if v not in (None, "", [], False)})
                    except (BlockedError, RateLimitError):
                        raise
                    except Exception as exc:
                        _logger.warning("detail fetch skipped id=%s: %s", raw.get("external_id"), exc)
                all_rows.append(self.normalize_record(raw))
                if len(all_rows) >= max_records:
                    break
            if progress_callback:
                progress_callback(pages, len(all_rows), page.exhausted)
            if page.exhausted or not page.next_cursor:
                break
            cursor = page.next_cursor
        return all_rows


def fold_key(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def header_case(name: str) -> str:
    """Title-Case a header name; keep sec-ch-ua* casing used by Chromium."""
    lower = (name or "").lower()
    special = {
        "user-agent": "User-Agent",
        "accept-language": "Accept-Language",
        "cache-control": "Cache-Control",
        "sec-ch-ua": "sec-ch-ua",
        "sec-ch-ua-mobile": "sec-ch-ua-mobile",
        "sec-ch-ua-platform": "sec-ch-ua-platform",
        "sec-fetch-site": "Sec-Fetch-Site",
        "sec-fetch-mode": "Sec-Fetch-Mode",
        "sec-fetch-user": "Sec-Fetch-User",
        "sec-fetch-dest": "Sec-Fetch-Dest",
        "upgrade-insecure-requests": "Upgrade-Insecure-Requests",
    }
    if lower in special:
        return special[lower]
    return "-".join(p.capitalize() for p in lower.split("-"))


def parse_devtools_headers(blob: str) -> Dict[str, str]:
    """Parse a DevTools Request Headers paste into a lowercase-key dict.

    Supports:
    - ``Cookie: value`` / ``user-agent: value`` lines
    - Chrome DevTools name/value pairs on alternating lines
      (``cookie`` then next line ``vid=...; cf_clearance=...``)
    """
    out: Dict[str, str] = {}
    if not blob:
        return out
    wanted = {
        "cookie", "user-agent", "accept", "accept-language",
        "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "referer",
    }
    lines = [ln.strip() for ln in blob.splitlines()]
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line or re.match(r"^(GET|POST|HEAD|PUT|DELETE)\s+", line, re.I):
            continue
        # Format A: "Header-Name: value"
        if ":" in line and not line.startswith(":"):
            key, val = line.split(":", 1)
            key = key.strip().lower()
            val = val.strip()
            if key in wanted and val:
                out[key] = val
                continue
            # "cookie:" with empty value — value may be next line
            if key in wanted and not val and i < len(lines) and lines[i]:
                out[key] = lines[i]
                i += 1
            continue
        # Format B: header name alone (Chrome DevTools copy), value on next line
        key = line.lower()
        if key.startswith(":"):
            # Skip HTTP/2 pseudo headers; also skip their following value line.
            if i < len(lines) and not lines[i].lower() in wanted and ":" not in lines[i]:
                i += 1
            continue
        if key in wanted and i < len(lines):
            val = lines[i]
            # Avoid treating another header name as the value.
            if val and val.lower() not in wanted and not val.startswith(":"):
                out[key] = val
                i += 1
    return out


def browser_headers_for_ua(ua: str) -> Dict[str, str]:
    """Build Chrome-like document headers derived from a pasted User-Agent."""
    ua = ua or ""
    mobile = bool(re.search(r"Mobile|Android", ua, re.I)) and "iPad" not in ua
    chrome_m = re.search(r"Chrome/(\d+)", ua)
    ver = chrome_m.group(1) if chrome_m else "120"
    if "Android" in ua:
        platform = '"Android"'
    elif "Windows" in ua:
        platform = '"Windows"'
    elif "Mac OS X" in ua or "Macintosh" in ua:
        platform = '"macOS"'
    else:
        platform = '"Linux"'
    sec_ch_ua = '"Not;A=Brand";v="8", "Chromium";v="%s", "Google Chrome";v="%s"' % (ver, ver)
    return {
        "User-Agent": ua,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.7"
        ),
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "sec-ch-ua": sec_ch_ua,
        "sec-ch-ua-mobile": "?1" if mobile else "?0",
        "sec-ch-ua-platform": platform,
    }


def urlstartswith_host(url: str, base: str) -> bool:
    try:
        return urlparse(url).netloc.endswith(urlparse(base).netloc)
    except Exception:
        return False


def _to_float(val):
    if val in (None, "", False):
        return False
    digits = re.sub(r"[^\d.,]", "", str(val)).replace(".", "").replace(",", ".")
    try:
        return float(digits)
    except ValueError:
        return False


def _to_bool(val):
    if val in (None, "", False):
        return False
    t = str(val).strip().lower()
    if t in ("var", "evet", "yes", "true", "1", "available"):
        return True
    if t in ("yok", "hayır", "hayir", "no", "false", "0"):
        return False
    return bool(t)
