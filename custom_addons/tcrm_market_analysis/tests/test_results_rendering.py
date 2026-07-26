# -*- coding: utf-8 -*-
from tcrm.tests import tagged

from ..services.demo_seed import seed_company_demo
from .common import MarketAnalysisCommon


@tagged("tcrm_market_analysis", "post_install", "-at_install")
class TestResultsRendering(MarketAnalysisCommon):
    def test_overview_and_listing_payload(self):
        env = self.env(context=dict(self.env.context, tcrm_market_allow_master_company_ops=True))
        seed_company_demo(env, self.company_a, scenario="istanbul")
        Listing = self.env["tcrm.market.listing"].with_company(self.company_a)
        metrics = Listing.get_overview_metrics([("company_id", "=", self.company_a.id)])
        self.assertFalse(metrics.get("empty"))
        self.assertIn("asking_price", metrics)
        self.assertIn("label", metrics)
        self.assertIn("asking", metrics["label"].lower())

        rows = Listing.search_read(
            [("company_id", "=", self.company_a.id), ("state", "=", "active")],
            ["name", "asking_price", "province", "district", "transaction_type", "state"],
            limit=5,
        )
        self.assertTrue(rows)
        for row in rows:
            self.assertIn(row["transaction_type"], ("sale", "rent", "short_term_rent"))
            self.assertTrue(row["province"])
