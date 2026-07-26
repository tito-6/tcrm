# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import models


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "bus.listener.mixin"]
