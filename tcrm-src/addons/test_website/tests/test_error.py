import tcrm.tests
from tcrm.tools import mute_logger


@tcrm.tests.common.tagged('post_install', '-at_install')
class TestWebsiteError(tcrm.tests.HttpCase):

    @mute_logger('tcrm.addons.http_routing.models.ir_http', 'tcrm.http')
    def test_01_run_test(self):
        self.start_tour("/test_error_view", 'test_error_website')
