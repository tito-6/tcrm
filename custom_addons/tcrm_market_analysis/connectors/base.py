# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Base connector contract for authorized market sources."""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from tcrm.exceptions import UserError

_logger = logging.getLogger(__name__)


class ConnectorError(UserError):
    """User-facing connector failure."""


class AuthorizationError(ConnectorError):
    """Source is not authorized to run."""


class RateLimitError(ConnectorError):
    """Source reported a rate limit."""


class PermanentFailure(ConnectorError):
    """Non-retryable connector failure."""


@dataclass
class FetchPageResult:
    records: List[Dict[str, Any]] = field(default_factory=list)
    next_cursor: Optional[str] = None
    exhausted: bool = False


class BaseMarketConnector:
    """Repository-consistent connector interface.

    Subclasses must never scrape unauthorized HTML. Sahibinden stays disabled
    until authorization evidence and approved feed details are configured.
    """

    source_type: str = "base"
    display_name: str = "Base"

    DEFAULT_CAPABILITIES = {
        "taxonomy": False,
        "listing_search": True,
        "details": False,
        "pagination": True,
        "incremental": False,
        "seller_type": True,
        "organization": False,
        "coordinates": False,
        "images": False,
        "history": False,
        "removed_detection": True,
    }

    def __init__(self, env, source):
        self.env = env
        self.source = source
        self._kill_switch = False

    # --- controls -----------------------------------------------------------

    def assert_enabled(self):
        if self._kill_switch or not self.source.active or self.source.state != "enabled":
            raise ConnectorError(
                "Source '%s' is disabled or kill-switched." % self.source.display_name
            )

    def assert_authorized(self):
        if self.source.authorization_state != "authorized":
            raise AuthorizationError(
                "Source '%s' is not authorized. Configure permitted credentials "
                "and approval before running." % self.source.display_name
            )

    def validate_configuration(self) -> Dict[str, Any]:
        self.assert_enabled()
        return {"ok": True, "source_type": self.source_type}

    def test_connection(self) -> Dict[str, Any]:
        self.assert_enabled()
        self.assert_authorized()
        return {"ok": True, "message": "Connection OK"}

    def kill(self):
        self._kill_switch = True

    # --- fetch --------------------------------------------------------------

    def fetch_taxonomy(self) -> List[Dict[str, Any]]:
        return []

    def fetch_page(self, cursor: Optional[str] = None, **kwargs) -> FetchPageResult:
        raise NotImplementedError

    def fetch_detail(self, external_id: str) -> Dict[str, Any]:
        raise PermanentFailure("Detail fetch not supported for this source.")

    def normalize_record(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Map a raw record into listing field keys (pre-ORM)."""
        return dict(raw)

    def iter_pages(
        self,
        *,
        max_pages: int = 50,
        max_records: int = 5000,
        cursor: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        self.assert_enabled()
        self.assert_authorized()
        pages = 0
        total = 0
        while pages < max_pages and total < max_records:
            if self._kill_switch:
                raise ConnectorError("Kill switch engaged.")
            page = self.fetch_page(cursor=cursor)
            pages += 1
            for raw in page.records:
                yield self.normalize_record(raw)
                total += 1
                if total >= max_records:
                    break
            if page.exhausted or not page.next_cursor:
                break
            cursor = page.next_cursor

    @staticmethod
    def checksum_payload(payload: Any) -> str:
        data = payload if isinstance(payload, (bytes, bytearray)) else str(payload).encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def report_authorization_failure(self, message: str):
        _logger.warning("market connector auth failure source=%s: %s", self.source.id, message)
        self.source.sudo().write({
            "authorization_state": "unauthorized",
            "last_error": message[:2000],
            "health": "error",
        })

    def report_rate_limit(self, message: str):
        _logger.warning("market connector rate limit source=%s: %s", self.source.id, message)
        self.source.sudo().write({
            "rate_limit_state": "limited",
            "last_error": message[:2000],
            "health": "degraded",
        })

    def report_permanent_failure(self, message: str):
        _logger.error("market connector permanent failure source=%s: %s", self.source.id, message)
        self.source.sudo().write({
            "last_error": message[:2000],
            "health": "error",
            "state": "error",
        })
