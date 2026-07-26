# -*- coding: utf-8 -*-
import base64
import json

from tcrm.tests import tagged
from tcrm.exceptions import UserError

from ..services.demo_seed import generate_demo_rows, seed_company_demo
from .common import MarketAnalysisCommon


@tagged("tcrm_market_analysis", "post_install", "-at_install")
class TestMarketImportPipeline(MarketAnalysisCommon):
    def test_csv_import_idempotent(self):
        source = self._make_source(self.company_a, source_type="csv", name="CSV A")
        rows = generate_demo_rows("istanbul", company_marker="A")
        # build minimal CSV
        headers = [
            "external_id", "transaction_type", "category", "province", "district",
            "asking_price", "currency", "gross_m2", "rooms", "seller_type", "seller_id",
        ]
        lines = [",".join(headers)]
        for r in rows[:5]:
            lines.append(",".join(str(r.get(h, "") or "") for h in headers))
        payload = "\n".join(lines).encode("utf-8")

        job = self.env["tcrm.market.import.job"].create({
            "source_id": source.id,
            "company_id": self.company_a.id,
            "data_file": base64.b64encode(payload),
            "data_filename": "demo.csv",
            "job_type": "import",
            "tenant_db_name": self.env.cr.dbname,
        })
        job.action_run()
        Listing = self.env["tcrm.market.listing"]
        count1 = Listing.search_count([("company_id", "=", self.company_a.id), ("source_id", "=", source.id)])
        self.assertGreater(count1, 0)
        snaps1 = self.env["tcrm.market.listing.snapshot"].search_count([
            ("company_id", "=", self.company_a.id),
        ])

        job2 = self.env["tcrm.market.import.job"].create({
            "source_id": source.id,
            "company_id": self.company_a.id,
            "data_file": base64.b64encode(payload),
            "data_filename": "demo.csv",
            "job_type": "import",
            "tenant_db_name": self.env.cr.dbname,
        })
        job2.action_run()
        count2 = Listing.search_count([("company_id", "=", self.company_a.id), ("source_id", "=", source.id)])
        self.assertEqual(count1, count2)
        snaps2 = self.env["tcrm.market.listing.snapshot"].search_count([
            ("company_id", "=", self.company_a.id),
        ])
        self.assertEqual(snaps1, snaps2)
        self.assertEqual(job2.count_skipped, count1)

    def test_json_import_and_removed_not_sold(self):
        source = self._make_source(self.company_a, source_type="json", name="JSON A")
        rows = generate_demo_rows("istanbul", company_marker="JA")[:3]
        payload = json.dumps({"listings": rows}).encode("utf-8")
        job = self.env["tcrm.market.import.job"].create({
            "source_id": source.id,
            "company_id": self.company_a.id,
            "data_file": base64.b64encode(payload),
            "data_filename": "demo.json",
            "tenant_db_name": self.env.cr.dbname,
        })
        job.action_run()
        listing = self.env["tcrm.market.listing"].search([
            ("company_id", "=", self.company_a.id),
            ("source_id", "=", source.id),
        ], limit=1)
        listing.action_mark_removed_from_source()
        self.assertEqual(listing.state, "removed_from_source")
        self.assertNotEqual(listing.state, "sold")

    def test_demo_seed_two_companies_isolated(self):
        env = self.env(context=dict(self.env.context, tcrm_market_allow_master_company_seed=True))
        seed_company_demo(env, self.company_a, scenario="istanbul")
        seed_company_demo(env, self.company_b, scenario="ankara_izmir")
        Listing = self.env["tcrm.market.listing"]
        a_ids = set(Listing.search([("company_id", "=", self.company_a.id)]).ids)
        b_ids = set(Listing.search([("company_id", "=", self.company_b.id)]).ids)
        self.assertTrue(a_ids)
        self.assertTrue(b_ids)
        self.assertFalse(a_ids & b_ids)
        # company A should see istanbul markers
        a_provinces = set(Listing.search([("company_id", "=", self.company_a.id)]).mapped("province"))
        self.assertTrue(any("stanbul" in (p or "") for p in a_provinces))

    def test_job_refuses_wrong_tenant_db(self):
        source = self._make_source(self.company_a)
        job = self.env["tcrm.market.import.job"].create({
            "source_id": source.id,
            "company_id": self.company_a.id,
            "tenant_db_name": "some_other_tenant_db",
            "job_type": "demo_seed",
        })
        with self.assertRaises(UserError):
            job.action_run()
