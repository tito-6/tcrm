# -*- coding: utf-8 -*-
"""
NotebookLM list client using the per-user Research Hub cookie jar.

Talks to NotebookLM's undocumented batchexecute RPC (same surface as the
web UI). Fragile by nature — Google can change RPC ids without notice.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

_logger = logging.getLogger(__name__)

NOTEBOOK_ORIGIN = "https://notebooklm.google.com"
BATCHEXECUTE_URL = f"{NOTEBOOK_ORIGIN}/_/LabsTailwindUi/data/batchexecute"

# Known list-notebooks RPC ids (tried in order; Google rotates these).
_LIST_RPC_IDS = (
    "wXbhsf",  # ListRecentlyViewedNotebooks (historical)
    "rLM1Ne",  # alternate list
    "McwZYd",  # newer list variant seen in 2025/26 captures
)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class NotebookLMClientError(Exception):
    def __init__(self, message, *, code="error"):
        super().__init__(message)
        self.code = code


def _extract_csrf(html: str) -> str | None:
    for pattern in (
        r'"SNlM0e"\s*:\s*"([^"]+)"',
        r"SNlM0e['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]",
        r"data-sni-lm0e=['\"]([^'\"]+)['\"]",
    ):
        m = re.search(pattern, html)
        if m:
            return m.group(1)
    return None


def _extract_session_id(html: str) -> str | None:
    m = re.search(r'"FdrFJe"\s*:\s*"([^"]+)"', html)
    return m.group(1) if m else None


def _walk_notebooks(obj: Any, found: list[dict]) -> None:
    """Heuristically collect notebook-like dicts from nested batchexecute JSON."""
    if isinstance(obj, dict):
        # Common shapes: {id, title} or nested title/emoji fields
        nid = obj.get("id") or obj.get("notebookId") or obj.get("notebook_id")
        title = obj.get("title") or obj.get("name") or obj.get("notebookTitle")
        if isinstance(nid, str) and nid and isinstance(title, str) and title:
            found.append({
                "google_notebook_id": nid,
                "name": title,
                "description": obj.get("description") or obj.get("emoji") or "",
                "source_count": obj.get("sourceCount") or obj.get("source_count") or 0,
                "url": f"{NOTEBOOK_ORIGIN}/notebook/{nid}",
                "raw": obj,
            })
        for v in obj.values():
            _walk_notebooks(v, found)
    elif isinstance(obj, list):
        # Compact list rows: [id, title, ...]
        if (
            len(obj) >= 2
            and isinstance(obj[0], str)
            and isinstance(obj[1], str)
            and len(obj[0]) >= 8
            and not obj[0].startswith("http")
        ):
            # Avoid capturing random string pairs; require id-ish first element
            if re.match(r"^[A-Za-z0-9_-]{8,}$", obj[0]):
                found.append({
                    "google_notebook_id": obj[0],
                    "name": obj[1],
                    "description": "",
                    "source_count": 0,
                    "url": f"{NOTEBOOK_ORIGIN}/notebook/{obj[0]}",
                    "raw": obj,
                })
        for item in obj:
            _walk_notebooks(item, found)


def _parse_batchexecute_body(text: str) -> list[dict]:
    # Responses often start with )]}'\n
    cleaned = text.lstrip()
    if cleaned.startswith(")]}'"):
        cleaned = cleaned[4:].lstrip()
    notebooks: list[dict] = []
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Sometimes multi-chunk: take first JSON array
        m = re.search(r"(\[.*\])", cleaned, re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            return []
    _walk_notebooks(data, notebooks)
    # Deduplicate by id
    by_id = {}
    for nb in notebooks:
        by_id[nb["google_notebook_id"]] = nb
    return list(by_id.values())


def _parse_html_bootstrap(html: str) -> list[dict]:
    """Fallback: pull notebook ids/titles from homepage bootstrap blobs."""
    found: list[dict] = []
    # notebook/<id> links with nearby title
    for m in re.finditer(
        r'/notebook/([A-Za-z0-9_-]{8,})[^"]*"[^>]*>\s*([^<]{1,200})',
        html,
    ):
        found.append({
            "google_notebook_id": m.group(1),
            "name": re.sub(r"\s+", " ", m.group(2)).strip() or m.group(1),
            "description": "",
            "source_count": 0,
            "url": f"{NOTEBOOK_ORIGIN}/notebook/{m.group(1)}",
            "raw": {"from": "html"},
        })
    # Also scan for quoted id/title pairs in AF_initDataCallback payloads
    for m in re.finditer(
        r'\["([A-Za-z0-9_-]{12,})"\s*,\s*"([^"]{1,200})"\s*,',
        html,
    ):
        found.append({
            "google_notebook_id": m.group(1),
            "name": m.group(2),
            "description": "",
            "source_count": 0,
            "url": f"{NOTEBOOK_ORIGIN}/notebook/{m.group(1)}",
            "raw": {"from": "af_init"},
        })
    by_id = {}
    for nb in found:
        by_id[nb["google_notebook_id"]] = nb
    return list(by_id.values())


def session_looks_logged_in(sess) -> bool:
    """Heuristic: Google auth cookies present in jar."""
    names = set()
    try:
        for c in sess.cookies:
            names.add(c.name)
    except Exception:
        try:
            names = set(sess.cookies.get_dict().keys())
        except Exception:
            return False
    markers = {"SID", "HSID", "SSID", "__Secure-1PSID", "__Secure-3PSID", "SAPISID"}
    return bool(names & markers)


def list_notebooks(sess) -> list[dict]:
    """
    List notebooks for the Google account bound to ``sess`` (requests.Session).
    Raises NotebookLMClientError on auth/network failure.
    """
    if sess is None:
        raise NotebookLMClientError("No Google session. Connect Google first.", code="no_session")

    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": NOTEBOOK_ORIGIN + "/",
    }
    try:
        home = sess.get(NOTEBOOK_ORIGIN + "/", headers=headers, timeout=45)
    except Exception as exc:
        raise NotebookLMClientError(f"Could not reach NotebookLM: {exc}", code="network") from exc

    html = home.text or ""
    if home.status_code in (401, 403) or "accounts.google.com" in (home.url or ""):
        raise NotebookLMClientError(
            "Google session missing or expired. Use Connect Google / In-Page login.",
            code="auth",
        )
    if not session_looks_logged_in(sess) and "SNlM0e" not in html:
        raise NotebookLMClientError(
            "Not signed in to Google NotebookLM yet.",
            code="auth",
        )

    csrf = _extract_csrf(html)
    session_id = _extract_session_id(html)

    notebooks: list[dict] = []
    if csrf:
        for rpc_id in _LIST_RPC_IDS:
            try:
                notebooks = _batchexecute_list(sess, csrf, session_id, rpc_id)
            except Exception as exc:
                _logger.info("NotebookLM RPC %s failed: %s", rpc_id, exc)
                notebooks = []
            if notebooks:
                _logger.info("NotebookLM list via RPC %s → %s notebooks", rpc_id, len(notebooks))
                break

    if not notebooks:
        notebooks = _parse_html_bootstrap(html)
        if notebooks:
            _logger.info("NotebookLM list via HTML bootstrap → %s notebooks", len(notebooks))

    if not notebooks and not session_looks_logged_in(sess):
        raise NotebookLMClientError(
            "Signed-in cookies not found. Complete Google login in In-Page mode, then Sync.",
            code="auth",
        )

    return notebooks


def _batchexecute_list(sess, csrf: str, session_id: str | None, rpc_id: str) -> list[dict]:
    # batchexecute f.req envelope: [[["rpcId", args_json, null, "generic"]]]
    inner = json.dumps([[rpc_id, json.dumps([None]), None, "generic"]], separators=(",", ":"))
    form = {
        "f.req": inner,
        "at": csrf,
    }
    params = {"rpcids": rpc_id, "source-path": "/", "hl": "en"}
    if session_id:
        params["_reqid"] = "1"
        params["rt"] = "c"

    headers = {
        "User-Agent": _USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Accept": "*/*",
        "Origin": NOTEBOOK_ORIGIN,
        "Referer": NOTEBOOK_ORIGIN + "/",
        "X-Same-Domain": "1",
    }
    resp = sess.post(
        BATCHEXECUTE_URL,
        params=params,
        data=form,
        headers=headers,
        timeout=45,
    )
    if resp.status_code >= 400:
        raise NotebookLMClientError(
            f"batchexecute HTTP {resp.status_code}",
            code="rpc_http",
        )
    return _parse_batchexecute_body(resp.text or "")
