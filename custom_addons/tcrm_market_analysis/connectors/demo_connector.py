# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Deterministic fictional demo market feed (not real listings)."""
from typing import Any, Dict, List, Optional

from .base import BaseMarketConnector, FetchPageResult
from .registry import register


@register
class DemoMarketConnector(BaseMarketConnector):
    source_type = "demo"
    display_name = "Fictional Demo Generator"

    DEFAULT_CAPABILITIES = {
        **BaseMarketConnector.DEFAULT_CAPABILITIES,
        "taxonomy": True,
        "coordinates": True,
        "organization": True,
        "history": True,
        "removed_detection": True,
        "images": False,
    }

    def validate_configuration(self):
        self.assert_enabled()
        return {"ok": True, "source_type": self.source_type, "fictional": True}

    def test_connection(self):
        self.assert_enabled()
        self.assert_authorized()
        return {"ok": True, "message": "Demo generator ready (fictional data only)."}

    def fetch_taxonomy(self) -> List[Dict[str, Any]]:
        return [
            {"code": "residential", "name": "Residential"},
            {"code": "commercial", "name": "Commercial"},
            {"code": "land", "name": "Land"},
        ]

    def generate_records(self, scenario: str = "istanbul") -> List[Dict[str, Any]]:
        # Thin generator; full seed lives in services.demo_seed for idempotent ORM seeding.
        return []

    def fetch_page(self, cursor: Optional[str] = None, records=None, **kwargs) -> FetchPageResult:
        return FetchPageResult(records=records or [], next_cursor=None, exhausted=True)
