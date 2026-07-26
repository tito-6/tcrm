from tcrm.addons.account.tests.common import AccountTestInvoicingCommon
from tcrm.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from tcrm.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericESTbai(TestGenericLocalization):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()
        cls.company.l10n_es_tbai_tax_agency = 'bizkaia'
