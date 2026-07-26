from tcrm.addons.account_edi.tests.common import AccountTestInvoicingCommon
from tcrm.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from tcrm.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericCO(TestGenericLocalization):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('co')
    def setUpClass(cls):
        super().setUpClass()
