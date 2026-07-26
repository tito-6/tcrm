# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import models


class ResGroups(models.Model):
    _name = 'res.groups'
    _inherit = ["res.groups", "bus.listener.mixin"]
