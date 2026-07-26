# -*- coding: utf-8 -*-
from tcrm import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    propertio_role = fields.Selection([
        ('sales', 'Sales'),
        ('collection', 'Collection'),
        ('aftersales', 'After-Sales'),
        ('finance', 'Finance'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    ], string='Propertio Role', help='Role used for role-based dashboard and features.')
