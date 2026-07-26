# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
import json
from typing import Any, Dict, List, Optional

from .base import BaseMarketConnector, ConnectorError, FetchPageResult
from .registry import register


@register
class JsonMarketConnector(BaseMarketConnector):
    source_type = "json"
    display_name = "JSON Upload / Feed"

    DEFAULT_CAPABILITIES = {
        **BaseMarketConnector.DEFAULT_CAPABILITIES,
        "pagination": True,
        "incremental": True,
    }

    def validate_configuration(self):
        self.assert_enabled()
        return {"ok": True, "source_type": self.source_type}

    def test_connection(self):
        self.assert_enabled()
        self.assert_authorized()
        return {"ok": True, "message": "JSON connector ready."}

    def parse_bytes(self, data: bytes) -> List[Dict[str, Any]]:
        try:
            payload = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise ConnectorError("Invalid JSON payload: %s" % exc) from exc
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("listings", "items", "data", "records"):
                if isinstance(payload.get(key), list):
                    return payload[key]
            return [payload]
        raise ConnectorError("JSON root must be a list or object with a listings array.")

    def fetch_page(self, cursor: Optional[str] = None, records=None, **kwargs) -> FetchPageResult:
        return FetchPageResult(records=records or [], next_cursor=None, exhausted=True)
