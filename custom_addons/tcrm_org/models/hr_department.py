# -*- coding: utf-8 -*-
from tcrm import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    manager_user_id = fields.Many2one(
        "res.users",
        string="Yönetici (Kullanıcı)",
        domain="[('share', '=', False)]",
        help="Departman yöneticisi — organizasyon şemasında gösterilir.",
    )
    user_ids = fields.Many2many(
        "res.users",
        "tcrm_org_department_user_rel",
        "department_id",
        "user_id",
        string="Personel",
        domain="[('share', '=', False)]",
        help="Bu departmana bağlı kullanıcılar.",
    )
    crm_team_ids = fields.One2many("crm.team", "department_id", string="Satış Ekipleri")
    team_count = fields.Integer(compute="_compute_team_count")
    user_count = fields.Integer(compute="_compute_user_count")

    def _compute_team_count(self):
        for dept in self:
            dept.team_count = len(dept.crm_team_ids)

    def _compute_user_count(self):
        for dept in self:
            dept.user_count = len(dept.user_ids)

    def action_open_teams(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Ekipler",
            "res_model": "crm.team",
            "view_mode": "list,kanban,form",
            "domain": [("department_id", "=", self.id)],
            "context": {"default_department_id": self.id},
        }
