# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import fields, models


class ResourceTest(models.Model):
    _name = 'resource.test'
    _description = 'Test Resource Model'
    _inherit = ['resource.mixin']

    name = fields.Char()
