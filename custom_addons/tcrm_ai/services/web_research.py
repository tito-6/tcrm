# Part of TCRM AI. See LICENSE for details.
"""Provider-independent public internet research with SSRF protections."""
from __future__ import annotations

import ipaddress
import json
import logging
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any

_logger = logging.getLogger(__name__)

MAX_RESPONSE_BYTES = 512_000
MAX_REDIRECTS = 3
DEFAULT_TIMEOUT = 12
USER_AGENT = 'TCRM-AI-Research/1.0 (+https://tcrm.local)'

BLOCKED_HOST_SUFFIXES = (
    '.internal',
    '.local',
    '.localhost',
    '.intranet',
    '.corp',
)

METADATA_HOSTS = {
    'metadata.google.internal',
    'metadata.goog',
    '169.254.169.254',
}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript') and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip:
            return
        text = (data or '').strip()
        if text:
            self._chunks.append(text)

    def text(self) -> str:
        return ' '.join(self._chunks)


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_public_url(url: str, allowed_domains: list[str] | None = None, blocked_domains: list[str] | None = None) -> str:
    """Return normalized URL or raise ValueError. Blocks SSRF targets."""
    raw = (url or '').strip()
    if not raw or len(raw) > 2048:
        raise ValueError('invalid_url')
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError('unsupported_scheme')
    if parsed.username or parsed.password:
        raise ValueError('credentials_forbidden')
    host = (parsed.hostname or '').lower().rstrip('.')
    if not host or host in METADATA_HOSTS:
        raise ValueError('blocked_host')
    if host == 'localhost' or host.endswith('.localhost'):
        raise ValueError('blocked_host')
    if any(host.endswith(suf) for suf in BLOCKED_HOST_SUFFIXES):
        raise ValueError('blocked_host')
    for blocked in blocked_domains or []:
        b = (blocked or '').strip().lower().lstrip('.')
        if b and (host == b or host.endswith('.' + b)):
            raise ValueError('blocked_domain')
    allow = [d.strip().lower().lstrip('.') for d in (allowed_domains or []) if d and d.strip()]
    if allow and not any(host == d or host.endswith('.' + d) for d in allow):
        raise ValueError('domain_not_allowed')

    # Resolve DNS and reject private/link-local/metadata answers (anti rebinding).
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError('dns_failed') from exc
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _is_blocked_ip(ip) or str(ip) == '169.254.169.254':
            raise ValueError('private_ip')
    # Rebuild without fragment; keep path/query.
    return urllib.parse.urlunparse((
        parsed.scheme, parsed.netloc, parsed.path or '/', parsed.params, parsed.query, '',
    ))


def _http_get(url: str, timeout: int, redirects_left: int, allowed_domains, blocked_domains) -> tuple[str, bytes, str]:
    safe_url = validate_public_url(url, allowed_domains, blocked_domains)
    req = urllib.request.Request(safe_url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/json,text/plain;q=0.9,*/*;q=0.1',
    })
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        final_url = resp.geturl() or safe_url
        # Re-validate after redirects.
        if redirects_left < MAX_REDIRECTS and final_url != safe_url:
            validate_public_url(final_url, allowed_domains, blocked_domains)
        ctype = (resp.headers.get('Content-Type') or '').split(';')[0].strip().lower()
        data = resp.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            data = data[:MAX_RESPONSE_BYTES]
        return final_url, data, ctype


def extract_text_from_html(html_bytes: bytes) -> str:
    try:
        html = html_bytes.decode('utf-8', errors='replace')
    except Exception:
        html = html_bytes.decode('latin-1', errors='replace')
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        return re.sub(r'<[^>]+>', ' ', html)[:4000]
    return parser.text()[:4000]


def fetch_public_page(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
) -> dict[str, Any]:
    timeout = max(3, min(30, int(timeout or DEFAULT_TIMEOUT)))
    retrieved_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    try:
        final_url, data, ctype = _http_get(url, timeout, MAX_REDIRECTS, allowed_domains, blocked_domains)
    except Exception as exc:
        return {
            'ok': False,
            'error': type(exc).__name__,
            'url': url,
            'retrieved_at': retrieved_at,
        }
    snippet = ''
    title = final_url
    if 'html' in (ctype or '') or data[:32].lstrip().lower().startswith(b'<!doctype') or b'<html' in data[:200].lower():
        text = extract_text_from_html(data)
        snippet = text[:800]
        m = re.search(r'<title[^>]*>(.*?)</title>', data.decode('utf-8', errors='replace'), re.I | re.S)
        if m:
            title = re.sub(r'\s+', ' ', m.group(1)).strip()[:200] or title
    elif 'json' in (ctype or ''):
        try:
            snippet = json.dumps(json.loads(data.decode('utf-8', errors='replace')), ensure_ascii=False)[:800]
        except Exception:
            snippet = data.decode('utf-8', errors='replace')[:800]
    else:
        snippet = data.decode('utf-8', errors='replace')[:800]
    return {
        'ok': True,
        'title': title,
        'url': final_url,
        'snippet': snippet,
        'content_type': ctype,
        'retrieved_at': retrieved_at,
        'source_type': 'internet',
    }


def _duckduckgo_search(query: str, limit: int, timeout: int) -> list[dict]:
    url = 'https://api.duckduckgo.com/?%s' % urllib.parse.urlencode({
        'q': query,
        'format': 'json',
        'no_html': 1,
        'skip_disambig': 1,
    })
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode('utf-8', errors='replace'))
    results = []
    abstract = (payload.get('AbstractText') or payload.get('Abstract') or '').strip()
    if abstract:
        results.append({
            'title': payload.get('Heading') or query,
            'snippet': abstract[:800],
            'url': payload.get('AbstractURL') or '',
            'published_at': '',
        })
    for topic in (payload.get('RelatedTopics') or [])[:limit]:
        if not isinstance(topic, dict):
            continue
        if topic.get('Text'):
            results.append({
                'title': (topic.get('Text') or '')[:120],
                'snippet': (topic.get('Text') or '')[:500],
                'url': topic.get('FirstURL') or '',
                'published_at': '',
            })
        for sub in topic.get('Topics') or []:
            if isinstance(sub, dict) and sub.get('Text'):
                results.append({
                    'title': (sub.get('Text') or '')[:120],
                    'snippet': (sub.get('Text') or '')[:500],
                    'url': sub.get('FirstURL') or '',
                    'published_at': '',
                })
        if len(results) >= limit:
            break
    return results[:limit]


def _brave_search(query: str, limit: int, timeout: int, api_key: str) -> list[dict]:
    url = 'https://api.search.brave.com/res/v1/web/search?%s' % urllib.parse.urlencode({
        'q': query,
        'count': limit,
    })
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/json',
        'X-Subscription-Token': api_key,
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode('utf-8', errors='replace'))
    results = []
    for item in ((payload.get('web') or {}).get('results') or [])[:limit]:
        results.append({
            'title': (item.get('title') or '')[:200],
            'snippet': (item.get('description') or '')[:800],
            'url': item.get('url') or '',
            'published_at': item.get('age') or item.get('page_age') or '',
        })
    return results


def _serper_search(query: str, limit: int, timeout: int, api_key: str) -> list[dict]:
    url = 'https://google.serper.dev/search'
    body = json.dumps({'q': query, 'num': limit}).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/json',
        'X-API-KEY': api_key,
    }, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode('utf-8', errors='replace'))
    results = []
    for item in (payload.get('organic') or [])[:limit]:
        results.append({
            'title': (item.get('title') or '')[:200],
            'snippet': (item.get('snippet') or '')[:800],
            'url': item.get('link') or '',
            'published_at': item.get('date') or '',
        })
    return results


def get_weather(city: str, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    city = (city or 'Istanbul').strip() or 'Istanbul'
    retrieved_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    path = urllib.parse.quote(city)
    url = 'https://wttr.in/%s?format=j1' % path
    try:
        validate_public_url(url)
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode('utf-8', errors='replace'))
        cur = (payload.get('current_condition') or [{}])[0]
        area = ((payload.get('nearest_area') or [{}])[0].get('areaName') or [{}])[0].get('value') or city
        desc = ((cur.get('weatherDesc') or [{}])[0].get('value')) or ''
        summary = (
            '%s: %s°C, hissedilen %s°C, nem %%%s, %s. Rüzgar %s km/s.'
            % (
                area,
                cur.get('temp_C') or '?',
                cur.get('FeelsLikeC') or '?',
                cur.get('humidity') or '?',
                desc,
                cur.get('windspeedKmph') or '?',
            )
        )
        return {
            'ok': True,
            'city': city,
            'summary': summary,
            'url': 'https://wttr.in/%s' % path,
            'source': 'wttr.in',
            'source_type': 'internet',
            'retrieved_at': retrieved_at,
            'citations': [{
                'title': 'Hava durumu — %s' % area,
                'url': 'https://wttr.in/%s' % path,
                'retrieved_at': retrieved_at,
            }],
        }
    except Exception as exc:
        _logger.info('weather lookup failed: %s', type(exc).__name__)
        return {
            'ok': False,
            'city': city,
            'error': type(exc).__name__,
            'retrieved_at': retrieved_at,
        }


def web_search(
    query: str,
    *,
    provider: str = 'duckduckgo',
    api_key: str = '',
    limit: int = 5,
    timeout: int = DEFAULT_TIMEOUT,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
) -> dict[str, Any]:
    q = (query or '').strip()
    retrieved_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    if not q:
        return {'ok': False, 'error': 'query_required', 'record_count': 0, 'retrieved_at': retrieved_at}
    limit = max(1, min(8, int(limit or 5)))
    timeout = max(3, min(30, int(timeout or DEFAULT_TIMEOUT)))
    provider = (provider or 'duckduckgo').strip().lower()
    results: list[dict] = []
    try:
        if provider == 'brave' and api_key:
            results = _brave_search(q, limit, timeout, api_key)
        elif provider == 'serper' and api_key:
            results = _serper_search(q, limit, timeout, api_key)
        else:
            results = _duckduckgo_search(q, limit, timeout)
    except Exception as exc:
        _logger.info('web_search provider=%s failed: %s', provider, type(exc).__name__)
        return {
            'ok': False,
            'query': q,
            'record_count': 0,
            'rows': [],
            'error': type(exc).__name__,
            'retrieved_at': retrieved_at,
            'source_type': 'internet',
            'note': 'Web araması şu an sonuç döndürmedi.',
        }

    # Filter result URLs against allow/block lists when present.
    filtered = []
    for row in results:
        url = row.get('url') or ''
        if not url:
            filtered.append(row)
            continue
        try:
            validate_public_url(url, allowed_domains, blocked_domains)
            filtered.append(row)
        except ValueError:
            continue

    citations = [{
        'title': r.get('title') or r.get('url'),
        'url': r.get('url'),
        'published_at': r.get('published_at') or '',
        'retrieved_at': retrieved_at,
    } for r in filtered if r.get('url')]

    return {
        'ok': True,
        'query': q,
        'record_count': len(filtered),
        'rows': filtered,
        'citations': citations,
        'provider': provider if provider in ('brave', 'serper') else 'duckduckgo',
        'data_source': 'internet',
        'source_type': 'internet',
        'retrieved_at': retrieved_at,
        'note': 'Cite these internet sources in the answer. Distinguish from TCRM business data.',
    }
