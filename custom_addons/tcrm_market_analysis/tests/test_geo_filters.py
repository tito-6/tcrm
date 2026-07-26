# -*- coding: utf-8 -*-
from tcrm.tests import tagged

from ..services import tr_geo
from .common import MarketAnalysisCommon


@tagged("tcrm_market_analysis", "post_install", "-at_install")
class TestGeoFilters(MarketAnalysisCommon):
    def test_il_autocomplete(self):
        hits = tr_geo.suggest_provinces("istan")
        names = [h["name"] for h in hits]
        self.assertTrue(any("stanbul" in n for n in names))
        # partial, case/diacritic insensitive
        hits2 = tr_geo.suggest_provinces("ANK")
        self.assertTrue(any(h["slug"] == "ankara" for h in hits2))

    def test_ilce_dependency(self):
        # Without province → empty
        self.assertEqual(tr_geo.suggest_districts("", "kad"), [])
        dists = tr_geo.suggest_districts("İstanbul", "kad")
        self.assertTrue(any(d["slug"] == "kadikoy" for d in dists))
        # Ankara must not return Kadıköy
        ankara = tr_geo.suggest_districts("Ankara", "kad")
        self.assertFalse(any(d["slug"] == "kadikoy" for d in ankara))
        self.assertTrue(any(d["slug"] == "cankaya" for d in tr_geo.suggest_districts("Ankara", "")))

    def test_mahalle_dependency(self):
        self.assertEqual(tr_geo.suggest_neighborhoods("İstanbul", "", "mod"), [])
        neigh = tr_geo.suggest_neighborhoods("İstanbul", "Kadıköy", "mod")
        self.assertTrue(any(n["slug"] == "moda" for n in neigh))
        # Wrong district → empty / no Moda
        other = tr_geo.suggest_neighborhoods("İstanbul", "Beşiktaş", "mod")
        self.assertFalse(any(n["slug"] == "moda" for n in other))

    def test_filter_generation_without_internal_ids(self):
        slugs = tr_geo.build_filter_slugs("İstanbul", "Kadıköy", "Moda")
        self.assertEqual(slugs["province_slug"], "istanbul")
        self.assertEqual(slugs["district_slug"], "kadikoy")
        self.assertEqual(slugs["neighborhood_slug"], "moda")
        self.assertEqual(slugs["province_name"], "İstanbul")
        # Human names only — no numeric IDs required
        self.assertFalse(str(slugs["province_slug"]).isdigit())
