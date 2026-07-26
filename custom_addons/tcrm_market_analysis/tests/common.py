# -*- coding: utf-8 -*-
from tcrm.tests import TransactionCase, tagged


@tagged("tcrm_market_analysis")
class MarketAnalysisCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Multi-company tests run on tcrm_master — explicit opt-in for listing writes.
        cls.env["ir.config_parameter"].sudo().set_param(
            "tcrm_market_analysis.allow_master_listings", "1"
        )
        cls.company_a = cls.env["res.company"].create({"name": "Market Tenant A"})
        cls.company_b = cls.env["res.company"].create({"name": "Market Tenant B"})
        Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.user_a = Users.create({
            "name": "Market User A",
            "login": "market_user_a_%s" % cls.company_a.id,
            "company_id": cls.company_a.id,
            "company_ids": [(6, 0, [cls.company_a.id])],
            "group_ids": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("tcrm_market_analysis.group_market_admin").id,
            ])],
        })
        cls.user_b = Users.create({
            "name": "Market User B",
            "login": "market_user_b_%s" % cls.company_b.id,
            "company_id": cls.company_b.id,
            "company_ids": [(6, 0, [cls.company_b.id])],
            "group_ids": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("tcrm_market_analysis.group_market_admin").id,
            ])],
        })
        cls.viewer_a = Users.create({
            "name": "Market Viewer A",
            "login": "market_viewer_a_%s" % cls.company_a.id,
            "company_id": cls.company_a.id,
            "company_ids": [(6, 0, [cls.company_a.id])],
            "group_ids": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("tcrm_market_analysis.group_market_viewer").id,
            ])],
        })

    def _make_source(self, company, source_type="csv", **kwargs):
        vals = {
            "name": kwargs.pop("name", "Test Source"),
            "source_type": source_type,
            "company_id": company.id,
            "authorization_state": "authorized",
            "state": "enabled",
        }
        vals.update(kwargs)
        return self.env["tcrm.market.source"].create(vals)
