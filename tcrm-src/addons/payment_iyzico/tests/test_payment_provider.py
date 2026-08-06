# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm.tests import tagged

from tcrm.addons.payment_iyzico.tests.common import IyzicoCommon


@tagged('post_install', '-at_install')
class TestPaymentProvider(IyzicoCommon):

    def test_signature_calculation_for_outgoing_data(self):
        """Test that the calculated signature matches the expected signature for outgoing data."""
        calculated_signature = self.provider._iyzico_calculate_signature(
            '/dummy', {'dummy': 'dummy'}, 'random_string'
        )
        expected_signature = 'ad5a61b79b941a805bb95aecac0ae2c9c4889fd92f534830be87c6b8d5d8fc2f'
        self.assertEqual(calculated_signature, expected_signature)
