# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
import csv
import io
from typing import Any, Dict, List, Optional

from .base import BaseMarketConnector, FetchPageResult
from .registry import register


@register
class CsvMarketConnector(BaseMarketConnector):
    source_type = "csv"
    display_name = "CSV Upload"

    DEFAULT_CAPABILITIES = {
        **BaseMarketConnector.DEFAULT_CAPABILITIES,
        "taxonomy": False,
        "pagination": False,
        "incremental": False,
    }

    def validate_configuration(self):
        self.assert_enabled()
        return {"ok": True, "source_type": self.source_type, "needs_upload": True}

    def test_connection(self):
        self.assert_enabled()
        self.assert_authorized()
        return {"ok": True, "message": "CSV connector ready for uploads."}

    def parse_bytes(self, data: bytes) -> List[Dict[str, Any]]:
        text = data.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        return [dict(row) for row in reader]

    def fetch_page(self, cursor: Optional[str] = None, records=None, **kwargs) -> FetchPageResult:
        rows = records or []
        return FetchPageResult(records=rows, next_cursor=None, exhausted=True)
