# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import models


class IrAttachment(models.Model):
    _name = 'ir.attachment'
    _inherit = ["ir.attachment", "bus.listener.mixin"]

    def _bus_channel(self):
        return self.env.user
