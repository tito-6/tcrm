# -*- coding: utf-8 -*-
"""Zernio REST client — Meta (IG/FB) publishing, inbox, ads, analytics.

API base: https://zernio.com/api/v1
Docs: https://docs.zernio.com/
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any

import requests

_logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = 'https://zernio.com/api/v1'
META_PLATFORMS = ('instagram', 'facebook')


class ZernioError(Exception):
    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class ZernioClient:
    """Bearer-auth client. API key never leaves the server."""

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL, timeout: int = 60):
        if not api_key:
            raise ZernioError('Zernio API anahtarı yapılandırılmamış.')
        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

    def _headers(self, *, idempotent: bool = False) -> dict[str, str]:
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        if idempotent:
            headers['x-request-id'] = str(uuid.uuid4())
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
        idempotent: bool = False,
    ) -> Any:
        url = f'{self.base_url}{path}'
        last_error: ZernioError | None = None
        for attempt in range(2):
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=self._headers(idempotent=idempotent),
                    params=params,
                    json=json_body,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                _logger.warning('Zernio network error: %s %s', method, path)
                raise ZernioError(f'Zernio bağlantı hatası: {exc}') from exc

            payload: Any = None
            if response.content:
                try:
                    payload = response.json()
                except ValueError:
                    payload = {'raw': (response.text or '')[:500]}

            if response.status_code in (401, 403):
                # Some Meta Ads endpoints return 403 for unsupported routes even when
                # the API key is valid (e.g. GET /ads/lead-forms on a metaads account).
                detail = None
                if isinstance(payload, dict):
                    detail = (
                        payload.get('error')
                        or payload.get('message')
                        or payload.get('msg')
                    )
                    if isinstance(detail, dict):
                        detail = detail.get('message') or str(detail)
                detail_text = str(detail or '').strip()
                if response.status_code == 403 and detail_text:
                    raise ZernioError(
                        detail_text,
                        status_code=response.status_code,
                        payload=payload,
                    )
                raise ZernioError(
                    'Zernio kimlik doğrulama hatası. API anahtarını kontrol edin.',
                    status_code=response.status_code,
                    payload=payload,
                )
            if response.status_code < 400:
                return payload if payload is not None else {}

            message = None
            if isinstance(payload, dict):
                message = (
                    payload.get('error')
                    or payload.get('message')
                    or payload.get('msg')
                )
                if isinstance(message, dict):
                    message = message.get('message') or str(message)
            err_text = str(message or f'Zernio HTTP {response.status_code}')
            last_error = ZernioError(
                err_text,
                status_code=response.status_code,
                payload=payload,
            )
            # Auto-backoff on rate limits
            is_rate = response.status_code == 429 or 'rate limit' in err_text.lower()
            if is_rate and attempt < 1:
                wait = 5
                m = re.search(r'retry after\s+(\d+)', err_text, flags=re.I)
                if m:
                    wait = min(int(m.group(1)) + 1, 20)
                _logger.info('Zernio rate limit; sleeping %ss (%s %s)', wait, method, path)
                time.sleep(wait)
                continue
            raise last_error
        raise last_error or ZernioError('Zernio request failed')

    # ------------------------------------------------------------------
    # Profiles
    # ------------------------------------------------------------------
    def list_profiles(self) -> list[dict]:
        data = self._request('GET', '/profiles')
        if isinstance(data, list):
            return data
        return list(data.get('profiles') or [])

    def create_profile(self, name: str, description: str | None = None) -> dict:
        body: dict[str, Any] = {'name': name}
        if description:
            body['description'] = description
        data = self._request('POST', '/profiles', json_body=body, idempotent=True)
        return data.get('profile') if isinstance(data, dict) else data

    # ------------------------------------------------------------------
    # Accounts / OAuth connect
    # ------------------------------------------------------------------
    def list_accounts(self, *, platform: str | None = None, profile_id: str | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if platform:
            params['platform'] = platform
        if profile_id:
            params['profileId'] = profile_id
        data = self._request('GET', '/accounts', params=params or None)
        if isinstance(data, list):
            return data
        return list(data.get('accounts') or [])

    def get_connect_url(
        self,
        platform: str,
        profile_id: str,
        *,
        redirect_url: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {'profileId': profile_id}
        if redirect_url:
            params['redirect_url'] = redirect_url
        return self._request('GET', f'/connect/{platform}', params=params)

    # ------------------------------------------------------------------
    # Posts
    # ------------------------------------------------------------------
    def list_posts(
        self,
        *,
        page: int = 1,
        limit: int = 50,
        platform: str | None = None,
        account_id: str | None = None,
        status: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {'page': page, 'limit': limit}
        if platform:
            params['platform'] = platform
        if account_id:
            params['accountId'] = account_id
        if status:
            params['status'] = status
        data = self._request('GET', '/posts', params=params)
        if isinstance(data, list):
            return {'posts': data, 'pagination': {}}
        return data if isinstance(data, dict) else {'posts': [], 'pagination': {}}

    def get_post(self, post_id: str) -> dict:
        data = self._request('GET', f'/posts/{post_id}')
        if isinstance(data, dict) and 'post' in data:
            return data['post']
        return data if isinstance(data, dict) else {}

    def create_post(self, body: dict) -> dict:
        data = self._request('POST', '/posts', json_body=body, idempotent=True)
        if isinstance(data, dict) and 'post' in data:
            return data['post']
        return data if isinstance(data, dict) else {}

    def delete_post(self, post_id: str) -> dict:
        return self._request('DELETE', f'/posts/{post_id}')

    def retry_post(self, post_id: str) -> dict:
        return self._request('POST', f'/posts/{post_id}/retry')

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------
    def get_analytics(self, *, limit: int = 25, sort_by: str = 'engagement') -> dict:
        return self._request(
            'GET',
            '/analytics',
            params={'limit': limit, 'sortBy': sort_by},
        )

    # ------------------------------------------------------------------
    # Inbox (DMs)
    # ------------------------------------------------------------------
    def list_conversations(
        self,
        *,
        platform: str | None = None,
        profile_id: str | None = None,
        account_id: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {'limit': limit}
        if platform:
            params['platform'] = platform
        if profile_id:
            params['profileId'] = profile_id
        if account_id:
            params['accountId'] = account_id
        if cursor:
            params['cursor'] = cursor
        return self._request('GET', '/inbox/conversations', params=params)

    def get_conversation(self, conversation_id: str, *, account_id: str) -> dict:
        data = self._request(
            'GET',
            f'/inbox/conversations/{conversation_id}',
            params={'accountId': account_id},
        )
        if isinstance(data, dict) and 'data' in data:
            return data['data']
        return data if isinstance(data, dict) else {}

    def list_messages(
        self,
        conversation_id: str,
        *,
        account_id: str,
        limit: int = 50,
    ) -> list[dict]:
        data = self._request(
            'GET',
            f'/inbox/conversations/{conversation_id}/messages',
            params={'accountId': account_id, 'limit': limit},
        )
        if isinstance(data, dict):
            return list(data.get('messages') or data.get('data') or [])
        return list(data or [])

    def send_inbox_message(
        self,
        conversation_id: str,
        *,
        account_id: str,
        message: str,
    ) -> dict:
        return self._request(
            'POST',
            f'/inbox/conversations/{conversation_id}/messages',
            json_body={'accountId': account_id, 'message': message},
            idempotent=True,
        )

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------
    def list_comments(
        self,
        *,
        platform: str | None = None,
        account_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        params: dict[str, Any] = {'limit': limit}
        if platform:
            params['platform'] = platform
        if account_id:
            params['accountId'] = account_id
        data = self._request('GET', '/inbox/comments', params=params)
        if isinstance(data, dict):
            return list(data.get('data') or data.get('comments') or [])
        return list(data or [])

    def reply_comment(
        self,
        post_id: str,
        *,
        account_id: str,
        message: str,
        comment_id: str | None = None,
        attachment_url: str | None = None,
    ) -> dict:
        body: dict[str, Any] = {
            'accountId': account_id,
            'message': message,
        }
        if comment_id:
            body['commentId'] = comment_id
        if attachment_url:
            body['attachmentUrl'] = attachment_url
        return self._request(
            'POST',
            f'/inbox/comments/{post_id}',
            json_body=body,
            idempotent=True,
        )

    # ------------------------------------------------------------------
    # Meta Ads
    # ------------------------------------------------------------------
    def list_ad_accounts(self, account_id: str) -> list[dict]:
        data = self._request('GET', '/ads/accounts', params={'accountId': account_id})
        if isinstance(data, dict):
            return list(data.get('accounts') or [])
        return list(data or [])

    def connect_facebook_ads(
        self,
        *,
        profile_id: str,
        account_id: str,
        ad_account_ids: list[str] | str | None = None,
    ) -> dict:
        """Ensure Meta Ads credential is connected / scoped to ad accounts."""
        params: dict[str, Any] = {
            'profileId': profile_id,
            'accountId': account_id,
        }
        if ad_account_ids:
            if isinstance(ad_account_ids, (list, tuple)):
                params['adAccountIds'] = ','.join(str(a) for a in ad_account_ids)
            else:
                params['adAccountIds'] = str(ad_account_ids)
        return self._request('GET', '/connect/facebook/ads', params=params)

    def connect_ads(
        self,
        platform: str,
        *,
        profile_id: str,
        account_id: str | None = None,
        ad_account_ids: list[str] | str | None = None,
    ) -> dict:
        """Unified ads connect — Meta/TikTok/Google (docs.zernio.com/connect/connect-ads)."""
        params: dict[str, Any] = {'profileId': profile_id}
        if account_id:
            params['accountId'] = account_id
        if ad_account_ids:
            if isinstance(ad_account_ids, (list, tuple)):
                params['adAccountIds'] = ','.join(str(a) for a in ad_account_ids)
            else:
                params['adAccountIds'] = str(ad_account_ids)
        return self._request('GET', f'/connect/{platform}/ads', params=params)

    def get_ads_tree(
        self,
        *,
        page: int = 1,
        limit: int = 50,
        source: str = 'all',
        ad_account_id: str | None = None,
        account_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {'page': page, 'limit': limit, 'source': source}
        if ad_account_id:
            params['adAccountId'] = ad_account_id
        if account_id:
            params['accountId'] = account_id
        if date_from:
            params['dateFrom'] = date_from
        if date_to:
            params['dateTo'] = date_to
        return self._request('GET', '/ads/tree', params=params)

    def list_keywords(
        self,
        *,
        page: int = 1,
        limit: int = 100,
        account_id: str | None = None,
        ad_account_id: str | None = None,
        campaign_id: str | None = None,
        status: str | None = None,
        match_type: str | None = None,
        negative: bool | None = None,
        search: str | None = None,
    ) -> dict:
        """GET /v1/ads/keywords — Google Search keyword criteria."""
        params: dict[str, Any] = {'page': page, 'limit': limit}
        if account_id:
            params['accountId'] = account_id
        if ad_account_id:
            params['adAccountId'] = ad_account_id
        if campaign_id:
            params['campaignId'] = campaign_id
        if status:
            params['status'] = status
        if match_type:
            params['matchType'] = match_type
        if negative is not None:
            params['negative'] = 'true' if negative else 'false'
        if search:
            params['search'] = search
        return self._request('GET', '/ads/keywords', params=params)

    def query_ad_insights(
        self,
        *,
        account_id: str,
        query: str,
        customer_id: str | None = None,
        page_token: str | None = None,
    ) -> dict:
        """GET /v1/ads/insights — Google GAQL passthrough (or Meta insights)."""
        params: dict[str, Any] = {'accountId': account_id, 'query': query}
        if customer_id:
            params['customerId'] = str(customer_id).replace('-', '')
        if page_token:
            params['pageToken'] = page_token
        return self._request('GET', '/ads/insights', params=params)

    def list_campaigns(
        self,
        *,
        page: int = 1,
        limit: int = 50,
        ad_account_id: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {'page': page, 'limit': limit}
        if ad_account_id:
            params['adAccountId'] = ad_account_id
        return self._request('GET', '/ads/campaigns', params=params)

    def list_ads(
        self,
        *,
        page: int = 1,
        limit: int = 50,
        ad_account_id: str | None = None,
        source: str = 'all',
        platform_ad_id: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {'page': page, 'limit': limit, 'source': source}
        if ad_account_id:
            params['adAccountId'] = ad_account_id
        if platform_ad_id:
            params['platformAdId'] = platform_ad_id
        return self._request('GET', '/ads', params=params)

    def get_ad(self, ad_id: str) -> dict:
        """GET /v1/ads/{adId} — accepts Zernio _id or Meta platformAdId.

        Falls back to list_ads(?platformAdId=) when path lookup 404s.
        """
        try:
            data = self._request('GET', f'/ads/{ad_id}')
            if isinstance(data, dict) and 'ad' in data:
                return data['ad']
            if isinstance(data, dict) and data.get('creative') is not None:
                return data
            if isinstance(data, dict) and data.get('_id'):
                return data
        except ZernioError as exc:
            _logger.debug('get_ad(%s) path failed: %s — trying platformAdId filter', ad_id, exc)
        # Fallback: filter list by Meta platform ad id (docs.zernio.com list-ads)
        try:
            listed = self.list_ads(platform_ad_id=str(ad_id), limit=5, source='all')
            ads = listed.get('ads') if isinstance(listed, dict) else None
            if ads:
                return ads[0]
        except ZernioError as exc:
            _logger.debug('list_ads(platformAdId=%s) failed: %s', ad_id, exc)
        return {}

    def create_standalone_ad(self, body: dict) -> dict:
        """POST /v1/ads/create — flat Meta campaign+ad body."""
        return self._request('POST', '/ads/create', json_body=body, idempotent=True)

    def boost_post(self, body: dict) -> dict:
        """POST /v1/ads/boost — promote an organic post."""
        return self._request('POST', '/ads/boost', json_body=body, idempotent=True)

    def update_campaign_status(
        self,
        campaign_id: str,
        *,
        status: str,
        platform: str = 'facebook',
    ) -> dict:
        return self._request(
            'PUT',
            f'/ads/campaigns/{campaign_id}/status',
            json_body={'status': status, 'platform': platform},
        )

    def update_campaign(
        self,
        campaign_id: str,
        body: dict,
    ) -> dict:
        return self._request('PUT', f'/ads/campaigns/{campaign_id}', json_body=body)

    def duplicate_campaign(
        self,
        campaign_id: str,
        *,
        platform: str = 'facebook',
    ) -> dict:
        return self._request(
            'POST',
            f'/ads/campaigns/{campaign_id}/duplicate',
            json_body={
                'platform': platform,
                'deepCopy': True,
                'statusOption': 'PAUSED',
                'renameStrategy': 'DEEP_RENAME',
                'renameSuffix': ' (kopya)',
            },
            idempotent=True,
        )

    # ------------------------------------------------------------------
    # Meta Lead Gen
    # ------------------------------------------------------------------
    def list_lead_forms(self, *, account_id: str, limit: int = 50, cursor: str | None = None) -> dict:
        params: dict[str, Any] = {'accountId': account_id, 'limit': limit}
        if cursor:
            params['cursor'] = cursor
        return self._request('GET', '/ads/lead-forms', params=params)

    def list_form_leads(
        self,
        form_id: str,
        *,
        account_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {'accountId': account_id, 'limit': limit}
        if cursor:
            params['cursor'] = cursor
        return self._request('GET', f'/ads/lead-forms/{form_id}/leads', params=params)

    def list_leads(
        self,
        *,
        account_id: str | None = None,
        form_id: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {'limit': limit}
        if account_id:
            params['accountId'] = account_id
        if form_id:
            params['formId'] = form_id
        if cursor:
            params['cursor'] = cursor
        return self._request('GET', '/ads/leads', params=params)

    # ------------------------------------------------------------------
    # Meta Ad Creatives & Image Library API
    # ------------------------------------------------------------------
    def list_ad_images(
        self,
        *,
        account_id: str,
        ad_account_id: str,
        fields: str | None = None,
        limit: int = 50,
        after: str | None = None,
    ) -> dict:
        """GET /v1/ads/images — Lists Meta ad account image library."""
        params: dict[str, Any] = {
            'accountId': account_id,
            'adAccountId': ad_account_id,
            'limit': limit,
        }
        if fields:
            params['fields'] = fields
        if after:
            params['after'] = after
        return self._request('GET', '/ads/images', params=params)

    def list_ad_creatives(
        self,
        *,
        account_id: str | None = None,
        ad_account_id: str | None = None,
        limit: int = 50,
    ) -> dict:
        """GET /v1/ads/creatives — Lists Meta ad creatives library."""
        params: dict[str, Any] = {'limit': limit}
        if account_id:
            params['accountId'] = account_id
        if ad_account_id:
            params['adAccountId'] = ad_account_id
        return self._request('GET', '/ads/creatives', params=params)
