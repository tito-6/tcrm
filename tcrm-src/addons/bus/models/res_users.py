# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import models


class ResUsers(models.Model):
    _name = "res.users"
    _inherit = ["res.users", "bus.listener.mixin"]

    def _bus_channel(self):
        return self.partner_id
