# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from werkzeug.urls import url_encode

from tcrm.tests import tagged
from tcrm.tools import mute_logger

from tcrm.addons.payment.tests.http_common import PaymentHttpCommon
from tcrm.addons.payment_iyzico import const
from tcrm.addons.payment_iyzico.tests.common import IyzicoCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(IyzicoCommon, PaymentHttpCommon):

    @mute_logger('tcrm.addons.payment_iyzico.controllers.main')
    def test_redirect_notification_triggers_processing(self):
        """Test that receiving a valid redirect notification triggers the processing of the
        payment data."""
        tx = self._create_transaction('redirect')
        url = self._build_url(
            f"{const.PAYMENT_RETURN_ROUTE}?{url_encode({'tx_ref': tx.reference})}"
        )
        with patch(
            'tcrm.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            return_value=self.payment_data
        ), patch(
            'tcrm.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ) as process_mock:
            self._make_http_post_request(url, data=self.return_data)
        self.assertEqual(process_mock.call_count, 1)

    @mute_logger('tcrm.addons.payment_iyzico.controllers.main')
    def test_webhook_notification_triggers_processing(self):
        """Test that receiving a valid webhook notification triggers the processing of the
        payment data."""
        self._create_transaction('redirect')
        url = self._build_url(const.WEBHOOK_ROUTE)
        with patch(
            'tcrm.addons.payment.models.payment_provider.PaymentProvider._send_api_request',
            return_value=self.payment_data
        ), patch(
            'tcrm.addons.payment.models.payment_transaction.PaymentTransaction._process'
        ) as process_mock:
            self._make_json_request(url, data=self.webhook_data)
        self.assertEqual(process_mock.call_count, 1)
