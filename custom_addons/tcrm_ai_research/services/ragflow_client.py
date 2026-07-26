# Part of TCRM AI Research. See LICENSE for details.
"""
RAGFlow HTTP client implementing BaseResearchProvider.

Endpoints follow the official RAGFlow HTTP API (v0.24+):
  POST /api/v1/datasets
  GET  /api/v1/datasets
  POST /api/v1/datasets/{id}/documents
  POST /api/v1/datasets/{id}/chunks
  GET  /api/v1/datasets/{id}/documents
  DELETE /api/v1/datasets/{id}/documents
  POST /api/v1/chats
  POST /api/v1/chats/{chat_id}/sessions
  POST /api/v1/chat/completions

Version-specific details stay encapsulated here.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Iterator

import requests

from .base_provider import BaseResearchProvider
from .config import get_ragflow_config
from .exceptions import (
    RagflowAuthError,
    RagflowError,
    RagflowNotFoundError,
    RagflowRateLimitError,
    RagflowTimeoutError,
    RagflowValidationError,
)

_logger = logging.getLogger(__name__)

# Safe to retry these HTTP methods / operations.
_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


class RagflowResearchProvider(BaseResearchProvider):
    """Server-side RAGFlow adapter. Never expose api_key to callers/logs."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: int = 60,
        max_retries: int = 3,
        session: requests.Session | None = None,
        correlation_id: str | None = None,
    ):
        if not base_url:
            raise RagflowValidationError('RAGFlow base URL is not configured')
        if not api_key:
            raise RagflowAuthError('RAGFlow API key is not configured')
        self.base_url = base_url.rstrip('/')
        self._api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.correlation_id = correlation_id or str(uuid.uuid4())

    # ------------------------------------------------------------------
    # Low-level HTTP
    # ------------------------------------------------------------------

    def _headers(self, content_type: str | None = 'application/json') -> dict[str, str]:
        headers = {
            'Authorization': f'Bearer {self._api_key}',
            'X-Correlation-ID': self.correlation_id,
        }
        if content_type:
            headers['Content-Type'] = content_type
        return headers

    def _url(self, path: str) -> str:
        return f'{self.base_url}{path}'

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.status_code in (401, 403):
            raise RagflowAuthError()
        if response.status_code == 404:
            raise RagflowNotFoundError()
        if response.status_code == 429:
            raise RagflowRateLimitError()
        if response.status_code >= 400:
            raise RagflowError(
                'RAGFlow request failed',
                category='http_error',
                status_code=response.status_code,
            )

    def _parse_json(self, response: requests.Response) -> Any:
        try:
            payload = response.json()
        except ValueError as exc:
            raise RagflowValidationError('Malformed JSON from RAGFlow') from exc
        if not isinstance(payload, dict):
            raise RagflowValidationError('Unexpected RAGFlow payload type')
        code = payload.get('code', 0)
        if code not in (0, None, '0'):
            message = payload.get('message') or 'RAGFlow returned an error'
            # Avoid leaking upstream stack traces / internal paths.
            safe = str(message)[:300]
            if 'auth' in safe.lower() or 'api key' in safe.lower():
                raise RagflowAuthError()
            if 'not found' in safe.lower() or "don't own" in safe.lower():
                raise RagflowNotFoundError(safe)
            raise RagflowError(safe, category='upstream')
        return payload.get('data', payload)

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        files: Any = None,
        params: dict | None = None,
        stream: bool = False,
        retry: bool = True,
    ) -> Any:
        url = self._url(path)
        content_type = None if files is not None else 'application/json'
        headers = self._headers(content_type)
        attempts = self.max_retries if retry else 1
        last_error: Exception | None = None
        started = time.monotonic()

        for attempt in range(1, attempts + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=headers,
                    json=json_body if files is None else None,
                    files=files,
                    params=params,
                    timeout=self.timeout,
                    stream=stream,
                )
                duration_ms = int((time.monotonic() - started) * 1000)
                _logger.info(
                    'ragflow_request correlation_id=%s method=%s path=%s '
                    'status=%s duration_ms=%s attempt=%s',
                    self.correlation_id,
                    method,
                    path,
                    response.status_code,
                    duration_ms,
                    attempt,
                )
                if response.status_code in _RETRYABLE_STATUS and attempt < attempts:
                    self._sleep_backoff(attempt, response.status_code)
                    continue
                self._raise_for_status(response)
                if stream:
                    return response
                return self._parse_json(response)
            except requests.Timeout as exc:
                last_error = RagflowTimeoutError()
                if attempt < attempts:
                    self._sleep_backoff(attempt)
                    continue
                raise last_error from exc
            except requests.RequestException as exc:
                last_error = RagflowError('RAGFlow connection error', category='connection')
                if attempt < attempts and method.upper() in ('GET', 'HEAD', 'DELETE'):
                    self._sleep_backoff(attempt)
                    continue
                raise last_error from exc
            except (RagflowRateLimitError, RagflowError) as exc:
                last_error = exc
                if isinstance(exc, RagflowRateLimitError) and attempt < attempts:
                    self._sleep_backoff(attempt, 429)
                    continue
                if (
                    isinstance(exc, RagflowError)
                    and exc.status_code in _RETRYABLE_STATUS
                    and attempt < attempts
                    and method.upper() in ('GET', 'HEAD', 'DELETE')
                ):
                    self._sleep_backoff(attempt, exc.status_code)
                    continue
                raise
        if last_error:
            raise last_error
        raise RagflowError('RAGFlow request failed after retries')

    @staticmethod
    def _sleep_backoff(attempt: int, status: int | None = None) -> None:
        # Exponential backoff; longer pause on rate limit.
        base = 0.5 * (2 ** (attempt - 1))
        if status == 429:
            base *= 2
        time.sleep(min(base, 8.0))

    # ------------------------------------------------------------------
    # Datasets
    # ------------------------------------------------------------------

    def create_dataset(self, name: str, **kwargs: Any) -> dict[str, Any]:
        body = {'name': name}
        for key in ('description', 'embedding_model', 'permission', 'chunk_method', 'parser_config'):
            if key in kwargs and kwargs[key] is not None:
                body[key] = kwargs[key]
        data = self._request('POST', '/api/v1/datasets', json_body=body)
        if not isinstance(data, dict) or not data.get('id'):
            raise RagflowValidationError('Dataset create response missing id')
        return data

    def list_datasets(self, name: str | None = None, **kwargs: Any) -> list[dict[str, Any]]:
        params: dict[str, Any] = {'page': kwargs.get('page', 1), 'page_size': kwargs.get('page_size', 30)}
        if name:
            params['name'] = name
        data = self._request('GET', '/api/v1/datasets', params=params)
        if isinstance(data, dict):
            items = data.get('docs') or data.get('data') or data.get('datasets') or []
            return items if isinstance(items, list) else []
        if isinstance(data, list):
            return data
        return []

    # ------------------------------------------------------------------
    # Chat assistants / sessions
    # ------------------------------------------------------------------

    def create_chat(self, name: str, dataset_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        body: dict[str, Any] = {'name': name, 'dataset_ids': dataset_ids}
        if kwargs.get('llm_id'):
            body['llm'] = {'model_name': kwargs['llm_id']}
        data = self._request('POST', '/api/v1/chats', json_body=body)
        if not isinstance(data, dict) or not data.get('id'):
            raise RagflowValidationError('Chat create response missing id')
        return data

    def create_session(self, chat_id: str, name: str = 'New session', **kwargs: Any) -> dict[str, Any]:
        data = self._request(
            'POST',
            f'/api/v1/chats/{chat_id}/sessions',
            json_body={'name': name},
        )
        if not isinstance(data, dict) or not data.get('id'):
            raise RagflowValidationError('Session create response missing id')
        return data

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def upload_document(
        self,
        dataset_id: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        files = {
            'file': (filename, content, content_type or 'application/octet-stream'),
        }
        data = self._request(
            'POST',
            f'/api/v1/datasets/{dataset_id}/documents',
            files=files,
            retry=False,
        )
        if isinstance(data, list) and data:
            doc = data[0]
        elif isinstance(data, dict):
            doc = data
        else:
            raise RagflowValidationError('Unexpected upload response')
        if not doc.get('id'):
            raise RagflowValidationError('Upload response missing document id')
        return doc

    def parse_documents(self, dataset_id: str, document_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        data = self._request(
            'POST',
            f'/api/v1/datasets/{dataset_id}/chunks',
            json_body={'document_ids': document_ids},
        )
        return data if isinstance(data, dict) else {'ok': True}

    def get_document_status(self, dataset_id: str, document_id: str, **kwargs: Any) -> dict[str, Any]:
        data = self._request(
            'GET',
            f'/api/v1/datasets/{dataset_id}/documents',
            params={'id': document_id, 'page': 1, 'page_size': 1},
        )
        docs: list = []
        if isinstance(data, dict):
            docs = data.get('docs') or data.get('documents') or []
        elif isinstance(data, list):
            docs = data
        if not docs:
            raise RagflowNotFoundError('Document not found in RAGFlow')
        doc = docs[0]
        run = (doc.get('run') or '').upper()
        return {
            'id': doc.get('id') or document_id,
            'name': doc.get('name'),
            'run': run,
            'progress': doc.get('progress'),
            'raw': {
                'chunk_count': doc.get('chunk_count'),
                'token_count': doc.get('token_count'),
                'size': doc.get('size'),
            },
        }

    def delete_document(self, dataset_id: str, document_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        data = self._request(
            'DELETE',
            f'/api/v1/datasets/{dataset_id}/documents',
            json_body={'ids': document_ids},
        )
        return data if isinstance(data, dict) else {'ok': True}

    # ------------------------------------------------------------------
    # Ask / chat completions
    # ------------------------------------------------------------------

    def ask(
        self,
        question: str,
        *,
        chat_id: str | None = None,
        session_id: str | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | Iterator[dict[str, Any]]:
        body: dict[str, Any] = {
            'question': question,
            'stream': bool(stream),
            'messages': [{'role': 'user', 'content': question}],
        }
        if chat_id:
            body['chat_id'] = chat_id
        if session_id:
            body['session_id'] = session_id

        if stream:
            return self._ask_stream(body)
        data = self._request(
            'POST',
            '/api/v1/chat/completions',
            json_body=body,
            retry=False,
        )
        return self._normalize_answer(data)

    def _ask_stream(self, body: dict[str, Any]) -> Iterator[dict[str, Any]]:
        response = self._request(
            'POST',
            '/api/v1/chat/completions',
            json_body=body,
            stream=True,
            retry=False,
        )
        try:
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                line = raw_line.strip()
                if line.startswith('data:'):
                    line = line[5:].strip()
                if not line or line == '[DONE]':
                    continue
                try:
                    payload = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(payload, dict):
                    continue
                data = payload.get('data', payload)
                if data is True:
                    yield {'done': True}
                    break
                if isinstance(data, dict):
                    yield self._normalize_answer(data, partial=True)
        finally:
            response.close()

    @staticmethod
    def _normalize_answer(data: Any, partial: bool = False) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise RagflowValidationError('Malformed chat completion payload')
        answer = data.get('answer') or data.get('content') or ''
        reference = data.get('reference') or {}
        chunks = []
        if isinstance(reference, dict):
            chunks = reference.get('chunks') or reference.get('doc_aggs') or []
        citations = []
        for chunk in chunks if isinstance(chunks, list) else []:
            if not isinstance(chunk, dict):
                continue
            citations.append({
                'title': chunk.get('document_name') or chunk.get('docnm_kwd') or chunk.get('title') or '',
                'page_number': chunk.get('page_number') or chunk.get('positions'),
                'chunk_text': chunk.get('content') or chunk.get('content_with_weight') or '',
                'source_url': chunk.get('url') or chunk.get('source_url') or '',
                'score': chunk.get('similarity') or chunk.get('score'),
                'external_reference': chunk.get('id') or chunk.get('chunk_id') or '',
                'document_external_id': chunk.get('document_id') or chunk.get('doc_id') or '',
            })
        return {
            'answer': answer,
            'session_id': data.get('session_id') or '',
            'message_id': data.get('id') or '',
            'citations': citations,
            'partial': partial,
            'raw_reference': reference if isinstance(reference, dict) else {},
        }


def get_research_provider(env, correlation_id: str | None = None) -> RagflowResearchProvider:
    """Factory: build a provider from env config (ICP + env vars)."""
    cfg = get_ragflow_config(env)
    return RagflowResearchProvider(
        base_url=cfg['base_url'],
        api_key=cfg['api_key'],
        timeout=cfg['timeout'],
        correlation_id=correlation_id,
    )
