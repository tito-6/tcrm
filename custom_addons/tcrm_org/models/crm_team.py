# -*- coding: utf-8 -*-
from tcrm import fields, models


class CrmTeam(models.Model):
    _inherit = "crm.team"

    department_id = fields.Many2one(
        "hr.department",
        string="Departman",
        check_company=True,
        help="Bu ekibin bağlı olduğu departman.",
    )
