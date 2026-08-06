# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import _
from tcrm.http import request
from tcrm.addons.im_livechat.controllers.main import LivechatController


class WebsiteLivechat(LivechatController):

    def _get_guest_name(self):
        visitor_sudo = request.env["website.visitor"]._get_visitor_from_request()
        return _('Visitor #%d', visitor_sudo.id) if visitor_sudo else super()._get_guest_name()
