from tcrm.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from tcrm.tests import tagged
from tcrm.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericCH(TestGenericLocalization):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ch')
    def setUpClass(cls):
        super().setUpClass()
