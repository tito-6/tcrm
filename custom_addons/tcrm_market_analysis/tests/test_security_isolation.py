# -*- coding: utf-8 -*-
from tcrm.tests import tagged
from tcrm.exceptions import AccessError

from ..services.demo_seed import seed_company_demo
from .common import MarketAnalysisCommon


@tagged("tcrm_market_analysis", "post_install", "-at_install")
class TestMarketSecurityIsolation(MarketAnalysisCommon):
    def test_cross_company_listing_isolation(self):
        env = self.env(context=dict(self.env.context, tcrm_market_allow_master_company_seed=True))
        seed_company_demo(env, self.company_a, scenario="istanbul")
        seed_company_demo(env, self.company_b, scenario="ankara_izmir")

        listing_a = self.env["tcrm.market.listing"].search([
            ("company_id", "=", self.company_a.id),
        ], limit=1)
        self.assertTrue(listing_a)

        ListingB = self.env["tcrm.market.listing"].with_user(self.user_b).with_company(self.company_b)
        leaked = ListingB.search([("id", "=", listing_a.id)])
        self.assertFalse(leaked)
        crafted = ListingB.search([
            ("id", "=", listing_a.id),
            ("company_id", "=", self.company_a.id),
        ])
        self.assertFalse(crafted)

    def test_secrets_not_in_non_admin_read(self):
        source = self.env["tcrm.market.source"].create({
            "name": "Secret Source",
            "source_type": "csv",
            "company_id": self.company_a.id,
            "authorization_state": "authorized",
            "state": "enabled",
            "credential_secret": "super-secret-token",
            "credential_ref": "vault://demo",
            "authorization_evidence": "CONTRACT-1",
        })
        SourceV = self.env["tcrm.market.source"].with_user(self.viewer_a).with_company(self.company_a)
        # Field-level groups block secret fields for viewers.
        with self.assertRaises(AccessError):
            SourceV.browse(source.id).read(["credential_secret"])
        row = SourceV.browse(source.id).read(["name", "source_type", "health"])[0]
        self.assertEqual(row["name"], "Secret Source")
        self.assertNotIn("credential_secret", row)

    def test_viewer_cannot_create_source(self):
        SourceV = self.env["tcrm.market.source"].with_user(self.viewer_a).with_company(self.company_a)
        with self.assertRaises(AccessError):
            SourceV.create({
                "name": "Should Fail",
                "source_type": "csv",
                "company_id": self.company_a.id,
                "authorization_state": "authorized",
                "state": "enabled",
            })

    def test_get_secure_config_admin_only(self):
        source = self._make_source(self.company_a, name="Cfg", credential_ref="ref-1")
        SourceV = self.env["tcrm.market.source"].with_user(self.viewer_a).with_company(self.company_a)
        with self.assertRaises(AccessError):
            SourceV.browse(source.id).get_secure_config()
