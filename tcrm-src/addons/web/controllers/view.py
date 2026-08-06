# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm.exceptions import AccessError
from tcrm.http import Controller, route, request
from tcrm.tools.translate import _


class View(Controller):

    @route('/web/view/edit_custom', type='jsonrpc', auth="user")
    def edit_custom(self, custom_id, arch):
        """
        Edit a custom view

        :param int custom_id: the id of the edited custom view
        :param str arch: the edited arch of the custom view
        :returns: dict with acknowledged operation (result set to True)
        """
        custom_view = request.env['ir.ui.view.custom'].sudo().browse(custom_id)
        if not custom_view.user_id == request.env.user:
            raise AccessError(_(
                "Custom view %(view)s does not belong to user %(user)s",
                view=custom_id,
                user=self.env.user.login,
            ))
        custom_view.write({'arch': arch})
        return {'result': True}
