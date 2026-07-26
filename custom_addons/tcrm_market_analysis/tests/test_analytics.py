# -*- coding: utf-8 -*-
from tcrm.tests import tagged

from ..services.analytics import (
    mean,
    median,
    percentile,
    summarize_prices,
    indicative_gross_yield,
    comparable_score,
)
from .common import MarketAnalysisCommon


@tagged("tcrm_market_analysis", "post_install", "-at_install")
class TestMarketAnalytics(MarketAnalysisCommon):
    def test_median_mean_percentiles(self):
        data = [10, 20, 30, 40, 50]
        self.assertEqual(median(data), 30)
        self.assertEqual(mean(data), 30)
        self.assertEqual(percentile(data, 25), 20)
        self.assertEqual(percentile(data, 75), 40)
        summary = summarize_prices(data)
        self.assertEqual(summary["count"], 5)
        self.assertEqual(summary["min"], 10)
        self.assertEqual(summary["max"], 50)

    def test_empty_and_single(self):
        self.assertIsNone(median([]))
        self.assertEqual(median([7]), 7)
        self.assertIsNone(indicative_gross_yield(None, 100))
        self.assertEqual(indicative_gross_yield(120000, 2400000), 5.0)

    def test_comparable_ranking_explainable(self):
        subject = {
            "transaction_type": "sale",
            "category_code": "residential",
            "province": "İstanbul",
            "district": "Kadıköy",
            "neighborhood": "Moda",
            "gross_area": 100,
            "rooms": "2+1",
        }
        good = dict(subject, state="active", quality_score=80)
        bad = {
            "transaction_type": "rent",
            "category_code": "land",
            "province": "Ankara",
            "district": "X",
            "neighborhood": "Y",
            "gross_area": 500,
            "rooms": "5+1",
            "state": "removed_from_source",
            "quality_score": 10,
        }
        s_good, f_good = comparable_score(subject, good)
        s_bad, f_bad = comparable_score(subject, bad)
        self.assertGreater(s_good, s_bad)
        self.assertIn("transaction_match", f_good)
        self.assertTrue(f_good)
