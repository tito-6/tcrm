from tcrm.tests import tagged
from tcrm.addons.website.tests.test_website_technical_page import TestWebsiteTechnicalPage


@tagged("post_install", "-at_install")
class TestWebsitePaymentTechnicalPage(TestWebsiteTechnicalPage):

    def test_load_website_payment_technical_pages(self):
        self._validate_routes([
            "/donation/pay",
            "/payment/status",
        ])
