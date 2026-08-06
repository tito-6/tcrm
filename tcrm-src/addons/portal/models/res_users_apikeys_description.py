# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import models, _
from tcrm.exceptions import AccessError


class ResUsersApikeysDescription(models.TransientModel):
    _inherit = 'res.users.apikeys.description'

    def check_access_make_key(self):
        try:
            return super().check_access_make_key()
        except AccessError:
            if self.env['ir.config_parameter'].sudo().get_param('portal.allow_api_keys'):
                if self.env.user._is_portal():
                    return
                else:
                    raise AccessError(_("Only internal and portal users can create API keys"))
            raise
