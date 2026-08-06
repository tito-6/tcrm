# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import tcrm
from tcrm.addons.point_of_sale.tests.common import CommonPosTest
from tcrm.exceptions import UserError


@tcrm.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(CommonPosTest):
    def test_pos_hr_session_name_gap(self):
        self.pos_config_usd.open_ui()
        session = self.pos_config_usd.current_session_id
        session.set_opening_control(0, None)
        current_session_name = session.name
        session.action_pos_session_closing_control()

        self.pos_config_usd.open_ui()
        session = self.pos_config_usd.current_session_id

        def _message_post_patch(*_args, **_kwargs):
            raise UserError('Test Error')

        with patch.object(self.env.registry.models['pos.session'], "message_post", _message_post_patch):
            with self.assertRaises(UserError):
                session.set_opening_control(0, None)

        session.set_opening_control(0, None)
        self.assertEqual(int(session.name.split('/')[1]), int(current_session_name.split('/')[1]) + 1)
