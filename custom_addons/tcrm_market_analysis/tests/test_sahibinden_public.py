# -*- coding: utf-8 -*-
from tcrm.tests import tagged
from tcrm.exceptions import UserError

from ..connectors import get_connector
from ..connectors.sahibinden import (
    BlockedError,
    SahibindenConnector,
    browser_headers_for_ua,
    parse_devtools_headers,
)
from ..services.import_pipeline import ImportPipeline
from .common import MarketAnalysisCommon

SAMPLE_SEARCH_HTML = """
<html><body>
<table>
<tr class="searchResultsItem" data-id="1234567890">
  <td><a class="classifiedTitle" href="/ilan/emlak-konut-satilik-daire-istanbul-kadikoy-moda-ornek-1234567890/detay">Moda Satılık Daire</a></td>
  <td class="searchResultsPriceValue">4.250.000 TL</td>
  <td class="searchResultsAttributeValue">3+1</td>
  <td class="searchResultsAttributeValue">120 m²</td>
  <td class="searchResultsLocationValue">İstanbul<br/>Kadıköy<br/>Moda</td>
  <td class="searchResultsDateValue">23-07-2026</td>
  <td><img src="https://example.com/img1.jpg"/></td>
</tr>
<tr class="searchResultsItem" data-id="1234567891">
  <td><a class="classifiedTitle" href="/ilan/emlak-konut-satilik-daire-istanbul-kadikoy-goztepe-ornek-1234567891/detay">Göztepe Satılık</a></td>
  <td class="searchResultsPriceValue">5.100.000 TL</td>
  <td class="searchResultsAttributeValue">2+1</td>
  <td class="searchResultsAttributeValue">95 m²</td>
  <td class="searchResultsLocationValue">İstanbul / Kadıköy / Göztepe</td>
</tr>
</table>
</body></html>
"""

CAPTCHA_HTML = """
<html><body><div class="g-recaptcha"></div><h1>Unusual traffic</h1></body></html>
"""


@tagged("tcrm_market_analysis", "post_install", "-at_install")
class TestSahibindenPublic(MarketAnalysisCommon):
    def _source(self, **kwargs):
        vals = {
            "name": "Sahibinden Public",
            "source_type": "sahibinden",
            "company_id": self.company_a.id,
            "authorization_state": "authorized",
            "state": "enabled",
            "filter_transaction": "sale",
            "filter_category": "daire",
            "filter_province": "İstanbul",
            "filter_district": "Kadıköy",
            "max_pages": 1,
            "max_records": 50,
        }
        vals.update(kwargs)
        return self.env["tcrm.market.source"].create(vals)

    def test_url_filter_generation(self):
        source = self._source()
        connector = get_connector(self.env, source)
        url = connector.build_search_url(
            transaction_type="sale",
            category="daire",
            province="İstanbul",
            district="Kadıköy",
            neighborhood="Moda",
        )
        self.assertIn("/satilik-daire/istanbul/kadikoy/moda", url)

    def test_parse_devtools_headers_dump(self):
        # Colon form
        parsed = parse_devtools_headers(
            "cookie: vid=1; cf_clearance=abc\n"
            "user-agent: Mozilla/5.0 (Linux; Android 15; Pixel 9) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Mobile Safari/537.36\n"
            'sec-ch-ua-mobile: ?1\n'
            'sec-ch-ua-platform: "Android"\n'
            "accept-language: en-US,en;q=0.9,tr;q=0.7\n"
        )
        self.assertEqual(parsed["cookie"], "vid=1; cf_clearance=abc")
        self.assertIn("Chrome/150", parsed["user-agent"])
        self.assertEqual(parsed["sec-ch-ua-mobile"], "?1")

        # Chrome DevTools alternating name / value lines (as copied from the panel)
        dump = (
            "Request URL\n"
            "https://www.sahibinden.com/satilik-daire\n"
            "Request Method\n"
            "GET\n"
            "Status Code\n"
            "200 OK\n"
            ":authority\n"
            "www.sahibinden.com\n"
            "cookie\n"
            "vid=1; cf_clearance=abc; __cf_bm=xyz\n"
            "user-agent\n"
            "Mozilla/5.0 (Linux; Android 15; Pixel 9) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Mobile Safari/537.36\n"
            "sec-ch-ua-mobile\n"
            "?1\n"
            "sec-ch-ua-platform\n"
            '"Android"\n'
            "accept-language\n"
            "en-US,en;q=0.9,tr;q=0.7\n"
        )
        parsed2 = parse_devtools_headers(dump)
        self.assertEqual(parsed2["cookie"], "vid=1; cf_clearance=abc; __cf_bm=xyz")
        self.assertIn("Pixel 9", parsed2["user-agent"])
        self.assertEqual(parsed2["sec-ch-ua-mobile"], "?1")
        self.assertEqual(parsed2["sec-ch-ua-platform"], '"Android"')

        headers = browser_headers_for_ua(parsed2["user-agent"])
        self.assertEqual(headers["sec-ch-ua-mobile"], "?1")
        self.assertEqual(headers["sec-ch-ua-platform"], '"Android"')
        self.assertIn('v="150"', headers["sec-ch-ua"])

        source = self._source(browser_cookie=dump, browser_user_agent="")
        connector = get_connector(self.env, source)
        session_headers = connector._parsed_browser_session()
        self.assertEqual(session_headers["Cookie"], "vid=1; cf_clearance=abc; __cf_bm=xyz")
        self.assertIn("Pixel 9", session_headers["User-Agent"])
        self.assertEqual(session_headers["sec-ch-ua-mobile"], "?1")

    def test_parse_search_and_collect(self):
        source = self._source()
        connector = get_connector(self.env, source)
        self.assertIsInstance(connector, SahibindenConnector)

        def fake_get(url):
            return 200, SAMPLE_SEARCH_HTML, url

        connector._http_get = fake_get
        rows = connector.collect(max_pages=1, max_records=10)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["external_id"], "1234567890")
        self.assertGreater(rows[0]["asking_price"], 0)
        self.assertIn("kadikoy", (rows[0].get("permitted_source_url") or "").lower())

    def test_blocked_stops_with_exact_error(self):
        source = self._source()
        connector = get_connector(self.env, source)

        def fake_get(url):
            return 403, "Access Denied", url

        connector._http_get = fake_get
        with self.assertRaises(BlockedError) as ctx:
            connector.collect(max_pages=1)
        self.assertIn("403", str(ctx.exception))
        self.assertIn("bypass", str(ctx.exception).lower())

    def test_captcha_page_stops(self):
        source = self._source()
        connector = get_connector(self.env, source)
        connector._http_get = lambda url: (200, CAPTCHA_HTML, url)
        with self.assertRaises(BlockedError) as ctx:
            connector.fetch_page(cursor="1")
        self.assertIn("captcha", str(ctx.exception).lower())

    def test_scrape_now_import_duplicates_and_history(self):
        source = self._source()
        connector = get_connector(self.env, source)
        connector._http_get = lambda url: (200, SAMPLE_SEARCH_HTML, url)

        job = self.env["tcrm.market.import.job"].create({
            "source_id": source.id,
            "company_id": self.company_a.id,
            "job_type": "scrape",
            "tenant_db_name": self.env.cr.dbname,
        })
        # Patch connector used inside job via source
        original = SahibindenConnector.collect

        def patched(self, **kwargs):
            self._http_get = lambda url: (200, SAMPLE_SEARCH_HTML, url)
            return original(self, **kwargs)

        SahibindenConnector.collect = patched
        try:
            job.action_run()
        finally:
            SahibindenConnector.collect = original

        Listing = self.env["tcrm.market.listing"]
        listings = Listing.search([
            ("company_id", "=", self.company_a.id),
            ("source_id", "=", source.id),
        ])
        self.assertEqual(len(listings), 2)
        snaps1 = self.env["tcrm.market.listing.snapshot"].search_count([
            ("company_id", "=", self.company_a.id),
        ])

        # Second scrape with price change → history snapshot, no duplicate listings
        html2 = SAMPLE_SEARCH_HTML.replace("4.250.000", "4.500.000")
        def patched2(self, **kwargs):
            self._http_get = lambda url: (200, html2, url)
            return original(self, **kwargs)
        SahibindenConnector.collect = patched2
        try:
            job2 = self.env["tcrm.market.import.job"].create({
                "source_id": source.id,
                "company_id": self.company_a.id,
                "job_type": "scrape",
                "tenant_db_name": self.env.cr.dbname,
            })
            job2.action_run()
        finally:
            SahibindenConnector.collect = original

        listings2 = Listing.search([
            ("company_id", "=", self.company_a.id),
            ("source_id", "=", source.id),
        ])
        self.assertEqual(len(listings2), 2)
        snaps2 = self.env["tcrm.market.listing.snapshot"].search_count([
            ("company_id", "=", self.company_a.id),
        ])
        self.assertGreater(snaps2, snaps1)
        changed = listings2.filtered(lambda l: l.external_listing_id == "1234567890")
        self.assertEqual(changed.asking_price, 4500000.0)

    def test_removed_listing_handling(self):
        source = self._source()
        original = SahibindenConnector.collect

        def first(self, **kwargs):
            self._http_get = lambda url: (200, SAMPLE_SEARCH_HTML, url)
            return original(self, **kwargs)

        SahibindenConnector.collect = first
        try:
            job = self.env["tcrm.market.import.job"].create({
                "source_id": source.id,
                "company_id": self.company_a.id,
                "job_type": "scrape",
                "tenant_db_name": self.env.cr.dbname,
            })
            job.action_run()
        finally:
            SahibindenConnector.collect = original

        # Only first listing remains in feed
        html_one = """
<html><body><table>
<tr class="searchResultsItem" data-id="1234567890">
  <td><a class="classifiedTitle" href="/ilan/emlak-konut-satilik-daire-istanbul-kadikoy-moda-ornek-1234567890/detay">Moda Satılık Daire</a></td>
  <td class="searchResultsPriceValue">4.250.000 TL</td>
  <td class="searchResultsLocationValue">İstanbul / Kadıköy / Moda</td>
</tr>
</table></body></html>
"""

        def second(self, **kwargs):
            self._http_get = lambda url: (200, html_one, url)
            return original(self, **kwargs)

        SahibindenConnector.collect = second
        try:
            job2 = self.env["tcrm.market.import.job"].create({
                "source_id": source.id,
                "company_id": self.company_a.id,
                "job_type": "scrape",
                "tenant_db_name": self.env.cr.dbname,
            })
            job2.action_run()
        finally:
            SahibindenConnector.collect = original

        removed = self.env["tcrm.market.listing"].search([
            ("company_id", "=", self.company_a.id),
            ("external_listing_id", "=", "1234567891"),
        ])
        self.assertEqual(removed.state, "removed_from_source")
        self.assertNotEqual(removed.state, "sold")

    def test_scrape_refuses_wrong_db_binding(self):
        source = self._source()
        job = self.env["tcrm.market.import.job"].create({
            "source_id": source.id,
            "company_id": self.company_a.id,
            "job_type": "scrape",
            "tenant_db_name": "other_tenant_db",
        })
        with self.assertRaises(UserError):
            job.action_run()
