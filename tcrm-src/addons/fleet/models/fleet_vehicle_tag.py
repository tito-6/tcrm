# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import fields, models


class FleetVehicleTag(models.Model):
    _name = 'fleet.vehicle.tag'
    _description = 'Vehicle Tag'

    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer('Color')

    _name_uniq = models.Constraint(
        'unique (name)',
        'Tag name already exists!',
    )
