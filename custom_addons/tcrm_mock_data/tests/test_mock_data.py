# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Backend tests for the TCRM mock-data scenario.

These validate the data created by ``tcrm.mock.builder`` (loaded on install):
idempotency, relational integrity, workflow states, payment-plan totals and the
cross-module bridges, plus the Phase-2 fixes (Discuss/Contacts app icons and the
dashboard action availability).
"""
from tcrm.tests.common import TransactionCase
from tcrm.tools import float_compare


class TestTcrmMockData(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.builder = cls.env["tcrm.mock.builder"]

    def _ref(self, xmlid):
        return self.env.ref("tcrm_mock_data.%s" % xmlid)

    # --- idempotency ---------------------------------------------------------
    def test_01_idempotent_build(self):
        """Re-running build_all() must not create duplicate records."""
        models = [
            "res.partner", "crm.lead", "propertio.project", "propertio.unit",
            "propertio.sale", "propertio.installment", "propertio.offer",
            "propertio.payment", "sale.order",
        ]
        before = {m: self.env[m].with_context(active_test=False).search_count([]) for m in models}
        self.builder.build_all()
        after = {m: self.env[m].with_context(active_test=False).search_count([]) for m in models}
        self.assertEqual(before, after, "build_all() is not idempotent: %s -> %s" % (before, after))

    def _scenario_projects(self):
        return self._ref("proj_nova_towers") | self._ref("proj_marina")

    def _scenario_units(self):
        return self.env["propertio.unit"].search([("project_id", "in", self._scenario_projects().ids)])

    def _scenario_sales(self):
        return self.env["propertio.sale"].browse(
            [self._ref(k).id for k in ("sale_a101", "sale_a102", "sale_c101")])

    # --- core presence -------------------------------------------------------
    def test_02_core_records_present(self):
        # Scope to the seeded scenario: a --test-enable run also loads dependency
        # demo data, so we must not assert on global counts.
        self.assertEqual(len(self._scenario_projects()), 2)
        self.assertEqual(len(self._scenario_units()), 12)
        self.assertEqual(len(self._scenario_sales()), 3)
        self.assertTrue(self.env["crm.lead"].search_count([("type", "=", "opportunity")]) >= 6)

    def test_02b_expanded_project_catalog(self):
        """Turkish types/stages and one demo project per type are available."""
        Type = self.env["propertio.project.type"]
        Stage = self.env["propertio.project.stage"]
        for code in (
            "konut", "villa", "ticari_dukkan", "karma", "devremulk",
            "arsa_parsel", "kentsel_donusum", "rezidans", "ofis", "sanayi_depo",
        ):
            self.assertTrue(
                Type.search_count([("code", "=", code)]) >= 1,
                "missing project type code %s" % code)
        for code in (
            "planlama", "ruhsat", "projelendirme", "satisa_hazir", "on_satista",
            "insaat_basladi", "insaat_devam", "teslime_hazir", "teslim_edildi",
            "tamamlandi", "durduruldu", "iptal",
        ):
            self.assertTrue(
                Stage.search_count([("code", "=", code)]) >= 1,
                "missing project stage code %s" % code)
        for xmlid in (
            "proj_villa_bodrum", "proj_ticari_bagdat", "proj_karma_ankara",
            "proj_devremulk_antalya", "proj_arsa_gebze", "proj_kentsel_kadikoy",
            "proj_ofis_maslak", "proj_sanayi_tosb", "proj_konut_bursa",
            "proj_villa_cesme", "proj_ticari_bostanci",
        ):
            proj = self.env.ref("tcrm_mock_data.%s" % xmlid, raise_if_not_found=False)
            self.assertTrue(proj, "missing expanded project %s" % xmlid)
            self.assertTrue(proj.type_id, "%s has no type" % xmlid)
            self.assertTrue(proj.stage_id, "%s has no stage" % xmlid)
        nova = self._ref("proj_nova_towers")
        marina = self._ref("proj_marina")
        self.assertEqual(nova.type_id.code, "konut")
        self.assertEqual(nova.stage_id.code, "on_satista")
        self.assertEqual(marina.type_id.code, "rezidans")
        self.assertEqual(marina.stage_id.code, "insaat_devam")
        for fold_code in ("teslim_edildi", "tamamlandi", "durduruldu", "iptal"):
            stage = Stage.search([("code", "=", fold_code)], limit=1)
            self.assertTrue(stage.fold, "%s should be folded" % fold_code)
    # --- relational integrity ------------------------------------------------
    def test_03_opportunity_links(self):
        """Opportunities reference the project + unit they are about."""
        for key in ("opp_a101", "opp_a102", "opp_c101", "opp_a103", "opp_c102"):
            opp = self._ref(key)
            self.assertTrue(opp.propertio_unit_id, "%s has no unit" % key)
            self.assertTrue(opp.propertio_project_id, "%s has no project" % key)
            self.assertEqual(opp.propertio_unit_id.project_id, opp.propertio_project_id)

    def test_04_sale_bridges(self):
        """Each property sale is linked to its opportunity and a broker agency."""
        for key in ("sale_a101", "sale_a102", "sale_c101"):
            sale = self._ref(key)
            self.assertTrue(sale.opportunity_id, "%s has no opportunity" % key)
            self.assertTrue(sale.agency_id.is_company, "%s broker must be a company" % key)
            self.assertEqual(sale.opportunity_id.propertio_unit_id, sale.unit_id,
                             "opportunity and sale must target the same unit")

    def test_05_sale_order_bridges(self):
        """Standard sale orders reference a CRM opportunity."""
        for key in ("so_a101", "so_a103", "so_c102"):
            so = self._ref(key)
            self.assertTrue(so.opportunity_id, "%s has no opportunity" % key)
            self.assertTrue(so.order_line, "%s has no order lines" % key)

    # --- workflow states -----------------------------------------------------
    def test_06_unit_states_consistent(self):
        units = self._scenario_units()
        self.assertEqual(len(units.filtered(lambda u: u.state == "sold")), 3)
        self.assertEqual(len(units.filtered(lambda u: u.state == "option")), 2)
        # A sold unit must have a confirmed contract.
        for key in ("sale_a101", "sale_a102", "sale_c101"):
            sale = self._ref(key)
            self.assertEqual(sale.state, "confirmed")
            self.assertEqual(sale.unit_id.state, "sold")
        # A reserved unit must have an offer.
        for key in ("offer_a103", "offer_c102"):
            offer = self._ref(key)
            self.assertEqual(offer.unit_id.state, "option")

    def test_07_no_sold_unit_is_available(self):
        sold_units = self.env["propertio.sale"].search([("state", "=", "confirmed")]).mapped("unit_id")
        for unit in sold_units:
            self.assertNotEqual(unit.state, "available",
                                "unit %s is both sold and available" % unit.display_name)

    # --- financial integrity -------------------------------------------------
    def test_08_installments_sum_to_price(self):
        for key in ("sale_a101", "sale_a102", "sale_c101"):
            sale = self._ref(key)
            total = sum(sale.installment_ids.mapped("amount"))
            self.assertEqual(
                float_compare(total, sale.sale_price, precision_digits=2), 0,
                "%s: installment plan %.2f != sale price %.2f" % (key, total, sale.sale_price))

    def test_09_payments_consistent(self):
        for key in ("sale_a101", "sale_a102", "sale_c101"):
            sale = self._ref(key)
            paid = sum(sale.installment_ids.mapped("amount_paid"))
            self.assertEqual(
                float_compare(paid, sale.total_paid, precision_digits=2), 0,
                "%s: paid installments %.2f != sale.total_paid %.2f" % (key, paid, sale.total_paid))
            self.assertGreater(sale.total_paid, 0, "%s should have a posted payment" % key)
            self.assertEqual(
                float_compare(sale.balance, sale.sale_price - sale.total_paid, precision_digits=2), 0,
                "%s: balance is inconsistent" % key)

    # --- Phase 2 fixes -------------------------------------------------------
    def test_10_app_icons_present(self):
        """Discuss and Contacts app menus must have their icon data (Phase 2A)."""
        for xmlid in ("mail.menu_root_discuss", "contacts.menu_contacts"):
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if not menu:
                continue
            self.assertTrue(menu.web_icon, "%s has no web_icon" % xmlid)
            self.assertTrue(menu.web_icon_data, "%s has empty web_icon_data" % xmlid)

    def test_11_dashboard_action_available(self):
        """The spreadsheet dashboard action is available and dashboards exist (Phase 2B)."""
        action = self.env.ref("spreadsheet_dashboard.ir_actions_dashboard_action", raise_if_not_found=False)
        self.assertTrue(action, "spreadsheet dashboard action missing")
        self.assertTrue(self.env["spreadsheet.dashboard"].search_count([]) > 0)
