# -*- coding: utf-8 -*-
"""
Research Hub — in-page reverse proxy for Google NotebookLM.

Why a reverse proxy (not a popup / direct iframe)
─────────────────────────────────────────────────
NotebookLM refuses framing (XFO/CSP). A naive HTML fetch also breaks Google
login because the Next button POSTs to accounts.google.com and expects cookies
on *.google.com.  Those never exist on the Odoo origin.

This controller:
  • Proxies GET/POST/PUT/PATCH/DELETE for allow-listed Google hosts
  • Keeps a **per-TCRM-user** cookie jar on the server (login lives in the iframe)
  • Rewrites HTML/JS absolute Google URLs to /tcrm/research/proxy/h/<host>/...
  • Injects a small bridge that patches fetch / XHR / form submits
  • Strips framing headers so the page can render inside TCRM
"""

from __future__ import annotations

import logging
import re
from urllib.parse import unquote, urljoin, urlparse

from werkzeug.wrappers import Response as WerkzeugResponse

from tcrm import http
from tcrm.http import request
from tcrm.exceptions import AccessDenied, UserError

from ..models import session_jar
from ..models import notebooklm_client

_logger = logging.getLogger(__name__)

NOTEBOOK_ORIGIN = "https://notebooklm.google.com"
PROXY_PREFIX = "/tcrm/research/proxy"
HAS_REQUESTS = session_jar.HAS_REQUESTS

_STRIP_HEADERS = frozenset([
    "x-frame-options",
    "content-security-policy",
    "content-security-policy-report-only",
    "content-encoding",
    "transfer-encoding",
    "content-length",
    "set-cookie",          # kept in server jar only
    "clear-site-data",
    "cross-origin-opener-policy",
    "cross-origin-embedder-policy",
    "cross-origin-resource-policy",
])

_ALLOWED_HOST_SUFFIXES = (
    ".google.com",
    ".googleapis.com",
    ".gstatic.com",
    ".googleusercontent.com",
    ".ggpht.com",
    ".youtube.com",
    ".ytimg.com",
)

_ALLOWED_HOSTS_EXACT = frozenset({
    "google.com",
    "googleapis.com",
    "gstatic.com",
    "youtube.com",
})

_HEAD_RE = re.compile(rb"<head(?:\s[^>]*)?>", re.IGNORECASE)
_ABS_URL_RE = re.compile(
    rb"""(?P<prefix>(?:href|src|action|poster)=["'])"""
    rb"""(?P<url>https?://[^"']+)""",
    re.IGNORECASE,
)
_CSS_URL_RE = re.compile(
    rb"""url\(\s*(?P<q>['"]?)(?P<url>https?://[^)'"]+)(?P=q)\s*\)""",
    re.IGNORECASE,
)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

def _host_allowed(host: str) -> bool:
    host = (host or "").lower().split(":")[0]
    if not host:
        return False
    if host in _ALLOWED_HOSTS_EXACT:
        return True
    return any(host.endswith(suf) for suf in _ALLOWED_HOST_SUFFIXES)


def _load_session(uid: int):
    return session_jar.load_session(uid)


def _save_session(uid: int, sess) -> None:
    session_jar.save_session(uid, sess)


def _proxy_url_for(absolute_url: str) -> str:
    parsed = urlparse(absolute_url)
    if parsed.scheme not in ("http", "https") or not _host_allowed(parsed.netloc):
        return absolute_url
    host = parsed.netloc
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    if parsed.fragment:
        path = f"{path}#{parsed.fragment}"
    # Keep path absolute under /h/<host>/
    return f"{PROXY_PREFIX}/h/{host}{path if path.startswith('/') else '/' + path}"


def _target_from_proxy_path(sub_path: str) -> str | None:
    """
    sub_path forms:
      ''                         -> notebooklm home
      'h/notebooklm.google.com'  -> https://notebooklm.google.com/
      'h/accounts.google.com/v3/signin/identifier' -> accounts URL
      legacy 'foo/bar'           -> https://notebooklm.google.com/foo/bar
    """
    sub_path = (sub_path or "").lstrip("/")
    if not sub_path:
        return NOTEBOOK_ORIGIN + "/"
    if sub_path.startswith("h/"):
        rest = sub_path[2:]
        if not rest:
            return None
        if "/" in rest:
            host, path = rest.split("/", 1)
            path = "/" + path
        else:
            host, path = rest, "/"
        host = unquote(host)
        if not _host_allowed(host):
            return None
        return f"https://{host}{path}"
    # Legacy single-host paths
    return f"{NOTEBOOK_ORIGIN}/{sub_path}"


def _rewrite_absolute_urls(body: bytes) -> bytes:
    def repl_attr(match: re.Match) -> bytes:
        prefix = match.group("prefix")
        url = match.group("url").decode("utf-8", errors="ignore")
        return prefix + _proxy_url_for(url).encode("utf-8")

    def repl_css(match: re.Match) -> bytes:
        q = match.group("q") or b""
        url = match.group("url").decode("utf-8", errors="ignore")
        return b"url(" + q + _proxy_url_for(url).encode("utf-8") + q + b")"

    body = _ABS_URL_RE.sub(repl_attr, body)
    body = _CSS_URL_RE.sub(repl_css, body)
    # Bare quoted absolute URLs in inline scripts (common in Google bootstraps)
    def repl_quoted(match: re.Match) -> bytes:
        q = match.group(1)
        url = match.group(2).decode("utf-8", errors="ignore")
        return q + _proxy_url_for(url).encode("utf-8") + q

    body = re.sub(
        rb"(['\"])(https?://(?:[a-z0-9.-]+\.)?(?:google|googleapis|gstatic|googleusercontent|youtube|ytimg)\.[a-z.]+[^'\"]*)\1",
        repl_quoted,
        body,
        flags=re.IGNORECASE,
    )
    return body


_BRIDGE_JS = r"""
<script id="tcrm-rhub-bridge">
(function () {
  var PREFIX = "%s";
  function allowed(host) {
    host = (host || "").toLowerCase();
    if (!host) return false;
    var suf = [".google.com",".googleapis.com",".gstatic.com",".googleusercontent.com",".ggpht.com",".youtube.com",".ytimg.com"];
    if (host === "google.com" || host === "googleapis.com" || host === "gstatic.com" || host === "youtube.com") return true;
    for (var i=0;i<suf.length;i++) if (host.endsWith(suf[i])) return true;
    return false;
  }
  function isNoopPath(path) {
    path = (path || "").toLowerCase();
    return path.indexOf("/jserror") === 0 || path.indexOf("/gen_204") === 0
        || path.indexOf("/csi") === 0 || path.indexOf("/log") === 0;
  }
  function toProxy(u) {
    try {
      var url = new URL(u, window.location.href);
      // Swallow Google client error beacons that would 404 on localhost
      if (isNoopPath(url.pathname) || url.hostname === "localhost" || url.hostname === "127.0.0.1") {
        if (isNoopPath(url.pathname) || (url.search || "").indexOf("jserror") >= 0) {
          return PREFIX + "/beacon";
        }
      }
      if (!allowed(url.hostname)) {
        // Relative Google paths under our proxy base
        if (url.origin === window.location.origin && url.pathname.indexOf(PREFIX) !== 0) {
          var m = window.location.pathname.match(new RegExp(PREFIX.replace(/\//g,"\\/") + "/h/([^/]+)"));
          if (m && m[1]) {
            return PREFIX + "/h/" + m[1] + url.pathname + url.search + url.hash;
          }
        }
        return u;
      }
      return PREFIX + "/h/" + url.host + url.pathname + url.search + url.hash;
    } catch (e) { return u; }
  }
  var _fetch = window.fetch;
  window.fetch = function (input, init) {
    try {
      if (typeof input === "string") input = toProxy(input);
      else if (input && input.url) input = new Request(toProxy(input.url), input);
    } catch (e) {}
    return _fetch.call(this, input, init);
  };
  var open = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url) {
    try { url = toProxy(url); } catch (e) {}
    return open.apply(this, [method, url].concat([].slice.call(arguments, 2)));
  };
  if (navigator.sendBeacon) {
    var _beacon = navigator.sendBeacon.bind(navigator);
    navigator.sendBeacon = function (url, data) {
      try { url = toProxy(url); } catch (e) {}
      try { return _beacon(url, data); } catch (e) { return true; }
    };
  }
  var _open = window.open;
  window.open = function (url) {
    if (url) url = toProxy(url);
    return _open.apply(this, [url].concat([].slice.call(arguments, 1)));
  };
  document.addEventListener("submit", function (ev) {
    try {
      var form = ev.target;
      if (form && form.action) form.action = toProxy(form.action);
    } catch (e) {}
  }, true);
  document.addEventListener("click", function (ev) {
    try {
      var a = ev.target && ev.target.closest ? ev.target.closest("a[href]") : null;
      if (a && a.href) {
        var proxied = toProxy(a.href);
        if (proxied !== a.href) a.href = proxied;
      }
    } catch (e) {}
  }, true);
})();
</script>
""".strip()


def _inject_bridge_and_base(html_bytes: bytes, base_href: str) -> bytes:
    html_bytes = _rewrite_absolute_urls(html_bytes)
    # Remove existing <base> tags — they break login when pointing at google.com
    html_bytes = re.sub(rb"<base\b[^>]*>", b"", html_bytes, flags=re.IGNORECASE)
    bridge = (_BRIDGE_JS % PROXY_PREFIX).encode("utf-8")
    base = f'<base href="{base_href}">'.encode("utf-8")
    inject = base + bridge
    match = _HEAD_RE.search(html_bytes)
    if not match:
        return inject + html_bytes
    return html_bytes[: match.end()] + inject + html_bytes[match.end() :]


class ResearchProxyController(http.Controller):

    def _check_master_access(self):
        user = request.env.user
        has_access = (
            user.has_group("base.group_system")
            or user.has_group("tcrm_saas_core.group_tcrm_tenant_admin")
            or user.has_group("tcrm_research_hub.group_research_hub_user")
        )
        if not has_access:
            raise AccessDenied("Research Hub: access denied.")

    def _tenant_has_entitlement(self) -> bool:
        env = request.env
        user = env.user
        if user.has_group("base.group_system"):
            return True
        module = env["ir.module.module"].sudo().search(
            [("name", "=", "tcrm_research_hub"), ("state", "=", "installed")],
            limit=1,
        )
        if not module:
            return user.has_group("tcrm_saas_core.group_tcrm_tenant_admin")
        tenant = env["tcrm.tenant"].sudo().search(
            [("company_id", "=", env.company.id)], limit=1
        )
        if not tenant:
            return user.has_group("tcrm_saas_core.group_tcrm_tenant_admin")
        entitlement = env["tcrm.tenant.module.entitlement"].sudo().search(
            [("tenant_id", "=", tenant.id), ("module_id", "=", module.id)],
            limit=1,
        )
        if not entitlement:
            return user.has_group("tcrm_saas_core.group_tcrm_tenant_admin")
        return entitlement.state != "blocked"

    @http.route(
        "/tcrm/research/status",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def research_status(self, **kw):
        self._check_master_access()
        uid = request.env.uid
        sess = _load_session(uid) if HAS_REQUESTS else None
        google_connected = bool(sess and notebooklm_client.session_looks_logged_in(sess))
        log = request.env["tcrm.research.sync.log"].sudo().search(
            [("user_id", "=", uid)], limit=1
        )
        synced_count = request.env["tcrm.research.notebook"].sudo().search_count([
            ("user_id", "=", uid),
            ("active", "=", True),
        ])
        return {
            "proxy_available": HAS_REQUESTS,
            "tenant_entitled": self._tenant_has_entitlement(),
            "target_url": NOTEBOOK_ORIGIN,
            "recommended_mode": "library",
            "proxy_auth_supported": True,
            "iframe_url": f"{PROXY_PREFIX}/h/notebooklm.google.com/",
            "google_connected": google_connected,
            "synced_count": synced_count,
            "last_sync_at": log.last_sync_at.isoformat() if log and log.last_sync_at else None,
            "last_sync_state": log.state if log else None,
            "last_sync_message": log.message if log else None,
        }

    @http.route(
        "/tcrm/research/sync",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def research_sync(self, **kw):
        """Fetch NotebookLM researches into TCRM DB for the current user."""
        self._check_master_access()
        if not self._tenant_has_entitlement():
            raise AccessDenied("Research Hub: not entitled.")
        try:
            result = request.env["tcrm.research.notebook"].action_sync_from_google()
            return {"ok": True, **result}
        except UserError as exc:
            return {"ok": False, "error": str(exc), "code": "sync_error"}
        except Exception as exc:
            _logger.exception("Research Hub sync failed")
            return {"ok": False, "error": str(exc), "code": "sync_error"}

    @http.route(
        "/tcrm/research/notebooks",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def research_notebooks(self, search="", **kw):
        self._check_master_access()
        domain = [("user_id", "=", request.env.uid), ("active", "=", True)]
        if search:
            domain.append(("name", "ilike", search))
        rows = request.env["tcrm.research.notebook"].sudo().search_read(
            domain,
            ["name", "google_notebook_id", "description", "url", "source_count", "synced_at"],
            limit=100,
            order="synced_at desc, name",
        )
        return {"notebooks": rows}

    @http.route(
        ["/jserror", "/gen_204", "/tcrm/research/proxy/beacon"],
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
        save_session=False,
    )
    def swallow_google_beacons(self, **kw):
        """Google Identity posts /jserror to the wrong origin under the proxy — return 204."""
        return request.make_response(b"", status=204)

    @http.route(
        "/tcrm/research/proxy/clear",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def clear_proxy_session(self, **kw):
        """Drop the server-side Google cookie jar for this TCRM user."""
        self._check_master_access()
        session_jar.clear_session(request.env.uid)
        return {"ok": True}

    @http.route(
        [
            "/tcrm/research/proxy",
            "/tcrm/research/proxy/",
            "/tcrm/research/proxy/<path:sub_path>",
        ],
        type="http",
        auth="user",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        csrf=False,
        save_session=False,
    )
    def proxy_notebook(self, sub_path="", **kw):
        try:
            self._check_master_access()
        except AccessDenied:
            return request.make_response(
                _ACCESS_DENIED_HTML,
                headers=[("Content-Type", "text/html; charset=utf-8")],
                status=403,
            )

        if not HAS_REQUESTS:
            return request.make_response(
                _PROXY_UNAVAILABLE_HTML,
                headers=[("Content-Type", "text/html; charset=utf-8")],
            )

        # Canonical entry: always land on host-scoped path so rewrites stay consistent.
        if not (sub_path or "").strip("/"):
            return request.redirect(f"{PROXY_PREFIX}/h/notebooklm.google.com/", code=302)

        target_url = _target_from_proxy_path(sub_path)
        if not target_url:
            return request.make_response(
                _proxy_error_html("Host not allowed for Research Hub proxy."),
                headers=[("Content-Type", "text/html; charset=utf-8")],
                status=400,
            )

        # Attach original query string if not already present in rewritten path.
        qs = request.httprequest.query_string.decode("utf-8", errors="replace")
        if qs and "?" not in target_url:
            target_url = f"{target_url}?{qs}"

        method = (request.httprequest.method or "GET").upper()
        if method == "OPTIONS":
            resp = WerkzeugResponse(response=b"", status=204)
            resp.headers["Access-Control-Allow-Origin"] = request.httprequest.host_url.rstrip("/")
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = request.httprequest.headers.get(
                "Access-Control-Request-Headers", "*"
            )
            return resp

        uid = request.env.uid
        sess = _load_session(uid)
        body = request.httprequest.get_data()
        parsed_target = urlparse(target_url)
        origin = f"{parsed_target.scheme}://{parsed_target.netloc}"

        # Upstream must look like a real browser hitting Google — never send
        # localhost/proxy URLs as Origin/Referer (Google Identity returns Throttled).
        is_nav = method == "GET" and "text/html" in (
            request.httprequest.headers.get("Accept") or ""
        )
        headers = {
            "User-Agent": request.httprequest.headers.get("User-Agent") or _USER_AGENT,
            "Accept": request.httprequest.headers.get(
                "Accept",
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            ),
            "Accept-Language": request.httprequest.headers.get(
                "Accept-Language", "en-US,en;q=0.9"
            ),
            "Referer": origin + "/",
            "Sec-Fetch-Dest": "document" if is_nav else "empty",
            "Sec-Fetch-Mode": "navigate" if is_nav else "cors",
            "Sec-Fetch-Site": "same-origin" if "google." in parsed_target.netloc else "cross-site",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        }
        # Only send Origin on mutating requests (GET+Origin can look automated).
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            headers["Origin"] = origin
        ct = request.httprequest.headers.get("Content-Type")
        if ct:
            headers["Content-Type"] = ct
        # Forward client referer only when it already maps to a Google URL via our proxy.
        client_ref = request.httprequest.headers.get("Referer") or ""
        if f"{PROXY_PREFIX}/h/" in client_ref:
            try:
                marker = f"{PROXY_PREFIX}/h/"
                idx = client_ref.find(marker)
                rest = client_ref[idx + len(marker) :]
                host, _, path = rest.partition("/")
                if _host_allowed(host):
                    headers["Referer"] = f"https://{host}/{path}"
            except Exception:
                pass
        for hname in (
            "X-Same-Domain",
            "X-Requested-With",
            "Google-Accounts-XSRF",
            "X-Goog-AuthUser",
            "X-Client-Data",
        ):
            hv = request.httprequest.headers.get(hname)
            if hv:
                headers[hname] = hv

        try:
            upstream = sess.request(
                method=method,
                url=target_url,
                data=body if method in ("POST", "PUT", "PATCH", "DELETE") else None,
                headers=headers,
                timeout=45,
                allow_redirects=False,
            )
        except Exception as exc:
            _logger.warning("Research Hub proxy error for %s: %s", target_url, exc)
            return request.make_response(
                _proxy_error_html(str(exc)),
                headers=[("Content-Type", "text/html; charset=utf-8")],
            )

        # Follow a short redirect chain server-side while keeping cookies in the jar.
        redirects = 0
        while upstream.is_redirect and redirects < 8:
            loc = upstream.headers.get("Location")
            if not loc:
                break
            next_url = urljoin(target_url, loc)
            parsed = urlparse(next_url)
            if parsed.scheme in ("http", "https") and _host_allowed(parsed.netloc):
                # Prefer returning a browser redirect into our proxy so the iframe URL updates
                # (needed for multi-step Google login).
                _save_session(uid, sess)
                return request.redirect(_proxy_url_for(next_url), code=302)
            # Non-google redirect — stop
            break

        _save_session(uid, sess)

        resp_body = upstream.content or b""
        content_type = upstream.headers.get("Content-Type", "application/octet-stream")

        ctype_l = content_type.lower()
        # Never rewrite identity / batchexecute / JSON — that triggers Throttled.
        skip_rewrite = any(
            x in (target_url or "")
            for x in (
                "/batchexecute",
                "identitytoolkit",
                "/v3/signin/_/",
                "/_/bscframe",
                "accounts.google.com/_/",
            )
        ) or "json" in ctype_l or "application/x-protobuffer" in ctype_l

        if "text/html" in ctype_l and not skip_rewrite:
            parsed = urlparse(target_url)
            path = parsed.path or "/"
            if path.endswith("/"):
                base_href = f"{PROXY_PREFIX}/h/{parsed.netloc}{path}"
            else:
                parent = path.rsplit("/", 1)[0] + "/"
                base_href = f"{PROXY_PREFIX}/h/{parsed.netloc}{parent}"
            resp_body = _inject_bridge_and_base(resp_body, base_href)
        elif (
            any(t in ctype_l for t in ("javascript", "ecmascript"))
            and "json" not in ctype_l
            and not skip_rewrite
        ):
            resp_body = _rewrite_absolute_urls(resp_body)

        resp = WerkzeugResponse(
            response=resp_body,
            status=upstream.status_code,
            content_type=content_type,
        )
        skip = {
            "content-type",
            "content-length",
            "transfer-encoding",
            "content-encoding",
            "location",
        }
        for k, v in upstream.headers.items():
            kl = k.lower()
            if kl in _STRIP_HEADERS or kl in skip:
                continue
            resp.headers[k] = v
        if upstream.is_redirect and upstream.headers.get("Location"):
            resp.headers["Location"] = _proxy_url_for(
                urljoin(target_url, upstream.headers["Location"])
            )
        resp.content_length = len(resp_body)
        return resp


_ACCESS_DENIED_HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{font:15px/1.6 sans-serif;display:flex;align-items:center;
justify-content:center;height:100vh;margin:0;color:#666}</style></head>
<body><div style="text-align:center">
<p style="font-size:2rem">🔒</p>
<p><strong>Research Hub access denied.</strong></p>
<p>Contact your system administrator.</p>
</div></body></html>
""".strip().encode()

_PROXY_UNAVAILABLE_HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{font:15px/1.6 sans-serif;display:flex;align-items:center;
justify-content:center;height:100vh;margin:0;color:#555}
code{background:#f4f4f4;padding:2px 6px;border-radius:4px;font-size:0.9em}
pre{background:#f4f4f4;padding:12px;border-radius:6px;margin-top:8px}</style></head>
<body><div style="text-align:center">
<p style="font-size:2rem">⚠️</p>
<p><strong>Proxy unavailable</strong></p>
<p>Install the <code>requests</code> package on the Odoo server:</p>
<pre>pip install requests</pre>
</div></body></html>
""".strip().encode()


def _proxy_error_html(message: str) -> bytes:
    safe_msg = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = f"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{font:15px/1.6 sans-serif;display:flex;align-items:center;
justify-content:center;height:100vh;margin:0;color:#555}}
pre{{background:#f4f4f4;padding:12px;border-radius:6px;max-width:600px;
word-break:break-all;white-space:pre-wrap}}</style></head>
<body><div style="text-align:center">
<p style="font-size:2rem">🚧</p>
<p><strong>Proxy fetch failed</strong></p>
<pre>{safe_msg}</pre>
</div></body></html>
""".strip()
    return html.encode()
