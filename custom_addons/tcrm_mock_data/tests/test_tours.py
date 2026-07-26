# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Browser (HttpCase) smoke tours for the TCRM frontend.

These verify, in a real browser, the Phase-2 fixes and that the seeded data
renders: the Discuss app icon, the dashboard (no tcrmDataProvider TDZ crash),
the CRM pipeline records and the promo-video-free Sales screen.

Tagged ``tcrm_tours`` (post_install) so they can be run on demand and do not
run in the fast backend-only suite.
"""
from tcrm.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "tcrm_tours")
class TestTcrmTours(HttpCase):

    def test_apps_and_crm(self):
        self.start_tour("/tcrm", "tcrm_apps_smoke", login="admin")

    def test_dashboard_renders(self):
        self.start_tour("/tcrm/dashboards?dashboard_id=4", "tcrm_dashboard_smoke",
                        login="admin", timeout=60)

    def test_sales_no_promo_video(self):
        self.start_tour("/tcrm/sales", "tcrm_sales_smoke", login="admin")
