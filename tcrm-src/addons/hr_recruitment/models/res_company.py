# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    job_properties_definition = fields.PropertiesDefinition("Job Properties")
