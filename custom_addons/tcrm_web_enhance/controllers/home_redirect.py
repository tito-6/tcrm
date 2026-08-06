# -*- coding: utf-8 -*-
"""Post-login redirect: open the user's Home Action in list view."""
from tcrm import http
from tcrm.http import request

from tcrm.addons.web.controllers.home import Home
from tcrm.addons.web.controllers.utils import is_user_internal


class TcrmHome(Home):
    def _login_redirect(self, uid, redirect=None):
        # Prefer an explicit redirect (e.g. deep-link), otherwise land on Home Action.
        if not redirect and uid and is_user_internal(uid):
            user = request.env['res.users'].sudo().browse(uid)
            action = user.action_id
            if action:
                # Force list when the home action is a window action with list mode.
                redirect = f'/tcrm/action-{action.id}?view_type=list'
        return super()._login_redirect(uid, redirect=redirect)
