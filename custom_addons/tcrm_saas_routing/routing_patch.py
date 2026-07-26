# -*- coding: utf-8 -*-
"""Host-based tenant database routing for TCRM (secure DB-per-tenant isolation).

Security model (production):
  * ``tcrm.online`` / ``www.tcrm.online``  -> control-plane DB (TCRM Master)
  * a **registered, active** tenant domain   -> that tenant's *explicitly mapped*
        database (``tcrm.tenant.db_name`` from ``tcrm_master``)
  * registered but suspended/frozen tenant   -> branded "suspended" page (503)
  * registered but not-yet-provisioned        -> branded "being prepared" page (503)
  * unknown subdomain                         -> branded "not found" page (404)

Hard guarantees:
  * The database name is **never** derived from the hostname string. The host is
    only used to look up the tenant record; the DB comes from the validated row.
  * The Odoo **database selector / manager** (``/web/database*``) is never served
    publicly (always 404).
  * Client-supplied ``X-tcrm-Database`` headers are stripped, so a client can
    never force a database.
  * One tenant host can never resolve to another tenant's (or the control) DB.

Reversible: remove ``tcrm_saas_routing`` from ``server_wide_modules`` and restart.
Fail-safe: any unexpected error serves a branded 503 for tenant hosts and never
falls back to exposing the control DB or the selector.
"""
import logging
import threading
import time

_logger = logging.getLogger(__name__)

try:
    from tcrm.tools import config
except Exception:  # pragma: no cover
    config = {}


def _cfg(key, default):
    try:
        val = config.get(key)
    except Exception:
        val = None
    return val if val not in (None, '') else default


CONTROL_DB = _cfg('tcrm_control_db', None) or 'tcrm_master'
BASE_DOMAIN = (_cfg('tcrm_base_domain', 'tcrm.online') or 'tcrm.online').lower().strip('.')
CONTROL_HOSTS = {
    h.strip().lower()
    for h in (_cfg('tcrm_control_hosts', 'tcrm.online') or '').split(',')
    if h.strip()
}
CONTROL_HOSTS.add(BASE_DOMAIN)
CONTROL_HOSTS.add('www.' + BASE_DOMAIN)

# Status constants
S_CONTROL = 'control'
S_OK = 'ok'
S_PREPARING = 'preparing'
S_SUSPENDED = 'suspended'
S_NOT_FOUND = 'not_found'
S_ERROR = 'error'

_MAP_TTL = 15.0   # seconds - host -> (status, db) cache
_DBS_TTL = 15.0   # seconds - server database list cache
_cache_lock = threading.Lock()
_host_cache = {}
_dbs_cache = {'ts': 0.0, 'dbs': frozenset()}

_MAPPING_SQL = """
    SELECT t.db_name, t.state, t.is_frozen, t.active, d.active
    FROM tcrm_tenant_domain d
    JOIN tcrm_tenant t ON t.id = d.tenant_id
    WHERE lower(d.domain) = %s
    ORDER BY d.is_primary DESC, d.id ASC
    LIMIT 1
"""


def normalize_host(host):
    """Lower-case host, strip port and trailing dot. Keeps leading ``www.``."""
    return (host or '').partition(':')[0].strip().rstrip('.').lower()


def _server_dbs():
    now = time.time()
    if now - _dbs_cache['ts'] < _DBS_TTL:
        return _dbs_cache['dbs']
    try:
        from tcrm.service import db as service_db
        dbs = frozenset(service_db.list_dbs(True))
    except Exception:
        _logger.exception('routing: list_dbs failed')
        dbs = _dbs_cache['dbs']  # keep last known
    _dbs_cache['ts'] = now
    _dbs_cache['dbs'] = dbs
    return dbs


def _query_mapping(host):
    """Return the raw mapping row for a host from the control DB, or None."""
    from tcrm.sql_db import db_connect
    conn = db_connect(CONTROL_DB)
    cr = conn.cursor()
    try:
        cr.execute(_MAPPING_SQL, (host,))
        return cr.fetchone()
    finally:
        cr.close()


def classify(row, db_exists):
    """Pure decision logic (unit-testable).

    ``row`` = (db_name, state, is_frozen, tenant_active, domain_active) | None
    ``db_exists`` = bool telling whether ``db_name`` is an existing server DB.
    """
    if not row:
        return (S_NOT_FOUND, None)
    db_name, state, is_frozen, tenant_active, domain_active = row
    if is_frozen or not tenant_active:
        return (S_SUSPENDED, None)
    if not domain_active:
        return (S_NOT_FOUND, None)
    if state != 'active' or not db_name:
        return (S_PREPARING, None)
    if not db_exists:
        return (S_PREPARING, None)
    return (S_OK, db_name)


def resolve_host(host):
    """Resolve a Host to (status, db). Cached with a short TTL.

    Control hosts short-circuit without touching the DB. Tenant hosts are
    resolved strictly from the tcrm_master domain->database mapping.
    """
    h = normalize_host(host)
    if not h or h in CONTROL_HOSTS or '.' not in h:
        return (S_CONTROL, CONTROL_DB)
    # Bare IP address -> control plane (health checks / direct IP access).
    if all(part.isdigit() for part in h.split('.') if part):
        return (S_CONTROL, CONTROL_DB)

    now = time.time()
    with _cache_lock:
        hit = _host_cache.get(h)
        if hit and now - hit[0] < _MAP_TTL:
            return hit[1]

    try:
        row = _query_mapping(h)
        db_exists = bool(row and row[0] and row[0] in _server_dbs())
        result = classify(row, db_exists)
    except Exception:
        _logger.exception('routing: mapping lookup failed for host %r', h)
        result = (S_ERROR, None)

    with _cache_lock:
        _host_cache[h] = (now, result)
    return result


# ---------------------------------------------------------------------------
# Branded (self-contained, DB-free) response pages
# ---------------------------------------------------------------------------
def _page(title, heading, message, accent='#0b1f3a'):
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'/>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
        "<meta name='robots' content='noindex,nofollow'/>"
        "<title>%s · TCRM</title><style>"
        "*{box-sizing:border-box}body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;"
        "background:#f4f6fb;color:#1b2436;display:flex;min-height:100vh;align-items:center;justify-content:center;padding:24px}"
        ".card{background:#fff;max-width:520px;width:100%%;border-radius:16px;box-shadow:0 12px 40px rgba(11,31,58,.12);"
        "padding:40px;text-align:center;border-top:5px solid %s}"
        ".brand{font-weight:800;letter-spacing:2px;color:%s;font-size:22px;margin-bottom:18px}"
        "h1{font-size:22px;margin:0 0 10px}p{color:#5b6577;line-height:1.6;margin:0 0 8px}"
        ".hint{font-size:13px;color:#8a93a6;margin-top:18px}"
        "a{color:%s;text-decoration:none;font-weight:600}"
        "</style></head><body><div class='card'><div class='brand'>TCRM</div>"
        "<h1>%s</h1><p>%s</p>"
        "<p class='hint'>TCRM · Powered by AK KOD &nbsp;|&nbsp; <a href='https://tcrm.online'>tcrm.online</a></p>"
        "</div></body></html>"
    ) % (title, accent, accent, accent, heading, message)


PAGE_NOT_FOUND = _page(
    "Tenant not found", "Tenant not found",
    "This address is not associated with any active TCRM workspace. "
    "Please check the URL, or contact your administrator.",
    accent='#b02a37')
PAGE_SUSPENDED = _page(
    "Workspace suspended", "This workspace is suspended",
    "Access to this TCRM workspace is currently suspended. "
    "Please contact TCRM support to restore access.",
    accent='#b8860b')
PAGE_PREPARING = _page(
    "Preparing workspace", "Your workspace is being prepared",
    "This TCRM workspace is still being set up. Please try again in a few minutes.",
    accent='#0b6bcb')
PAGE_ERROR = _page(
    "Temporarily unavailable", "Temporarily unavailable",
    "We could not route your request right now. Please try again shortly.",
    accent='#5b6577')

_STATUS_LINE = {200: '200 OK', 404: '404 Not Found', 503: '503 Service Unavailable'}


def _serve(start_response, code, html):
    body = html.encode('utf-8')
    headers = [
        ('Content-Type', 'text/html; charset=utf-8'),
        ('Content-Length', str(len(body))),
        ('X-Content-Type-Options', 'nosniff'),
        ('Cache-Control', 'no-store'),
    ]
    start_response(_STATUS_LINE.get(code, '%d Error' % code), headers)
    return [body]


def _middleware(environ, start_response):
    """Return a WSGI response iterable if the request must be short-circuited,
    otherwise ``None`` to let Odoo handle it."""
    try:
        path = environ.get('PATH_INFO', '') or ''

        # 1) Never expose the database selector / manager publicly.
        if path == '/web/database' or path.startswith('/web/database/'):
            return _serve(start_response, 404, PAGE_NOT_FOUND)

        # 2) Reject client-supplied database selection headers.
        environ.pop('HTTP_X_TCRM_DATABASE', None)
        environ.pop('HTTP_X_ODOO_DATABASE', None)

        host = environ.get('HTTP_HOST', '')
        status, _db = resolve_host(host)

        if status in (S_CONTROL, S_OK):
            return None  # pass through to Odoo (db_filter enforces the DB)
        if status == S_SUSPENDED:
            return _serve(start_response, 503, PAGE_SUSPENDED)
        if status == S_PREPARING:
            return _serve(start_response, 503, PAGE_PREPARING)
        if status == S_NOT_FOUND:
            return _serve(start_response, 404, PAGE_NOT_FOUND)
        return _serve(start_response, 503, PAGE_ERROR)
    except Exception:
        _logger.exception('routing middleware error')
        # Fail closed for safety: never leak the selector on error.
        return _serve(start_response, 503, PAGE_ERROR)


def _install_patch():
    import tcrm.http as tcrm_http

    # --- db_filter: DB is chosen strictly from the validated mapping ---
    original_db_filter = tcrm_http.db_filter

    def db_filter(dbs, host=None):
        try:
            if host is None:
                req = getattr(tcrm_http, 'request', None)
                if req is not None and getattr(req, 'httprequest', None) is not None:
                    host = req.httprequest.environ.get('HTTP_HOST', '')
            status, db = resolve_host(host)
            if status in (S_CONTROL, S_OK) and db:
                return [d for d in dbs if d == db]
            return []
        except Exception:
            _logger.exception('routing db_filter error; denying (empty)')
            return []

    tcrm_http.db_filter = db_filter

    # --- WSGI middleware for branded pages + selector lockdown ---
    App = type(tcrm_http.root)
    if getattr(App, '_tcrm_routing_wrapped', False):
        _logger.info('TCRM routing already wrapped; skipping')
    else:
        original_call = App.__call__

        def __call__(self, environ, start_response):
            handled = _middleware(environ, start_response)
            if handled is not None:
                return handled
            return original_call(self, environ, start_response)

        App.__call__ = __call__
        App._tcrm_routing_wrapped = True

    _logger.info(
        'TCRM secure tenant routing ACTIVE (control_db=%s, base_domain=%s, control_hosts=%s)',
        CONTROL_DB, BASE_DOMAIN, sorted(CONTROL_HOSTS),
    )


try:
    _install_patch()
except Exception:  # pragma: no cover
    _logger.exception('TCRM tenant routing could not be installed')
