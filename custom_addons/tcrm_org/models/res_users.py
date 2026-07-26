# -*- coding: utf-8 -*-
from tcrm import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    org_department_ids = fields.Many2many(
        "hr.department",
        "tcrm_org_department_user_rel",
        "user_id",
        "department_id",
        string="Departmanlar",
    )
    org_access_grant_ids = fields.One2many(
        "tcrm.org.access.grant",
        "user_id",
        string="Ekran Erişimleri",
    )

    def action_open_org_access(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Ekran Erişimi",
            "res_model": "tcrm.org.access.grant",
            "view_mode": "list,form",
            "domain": [("user_id", "=", self.id)],
            "context": {"default_user_id": self.id},
        }

    @api.model
    def _tcrm_org_feature_specs(self):
        """Curated grantable features → underlying res.groups xmlids."""
        return [
            {
                "code": "crm_sales",
                "name": "CRM / Satış (atanan kayıtlar)",
                "group_xmlids": ["sales_team.group_sale_salesman"],
                "sequence": 10,
            },
            {
                "code": "crm_all_leads",
                "name": "CRM — Tüm lead / fırsatlar",
                "group_xmlids": ["sales_team.group_sale_salesman_all_leads"],
                "sequence": 20,
            },
            {
                "code": "crm_manager",
                "name": "CRM — Ekip / yapılandırma yöneticisi",
                "group_xmlids": ["sales_team.group_sale_manager"],
                "sequence": 30,
            },
            {
                "code": "tenant_sales",
                "name": "Kiracı — Satış rolü",
                "group_xmlids": ["tcrm_saas_core.group_tcrm_tenant_sales"],
                "sequence": 40,
            },
            {
                "code": "tenant_ops",
                "name": "Kiracı — Operasyon",
                "group_xmlids": ["tcrm_saas_core.group_tcrm_tenant_operations"],
                "sequence": 50,
            },
            {
                "code": "tenant_finance",
                "name": "Kiracı — Finans",
                "group_xmlids": ["tcrm_saas_core.group_tcrm_tenant_finance"],
                "sequence": 60,
            },
            {
                "code": "tenant_manager",
                "name": "Kiracı — Yönetici",
                "group_xmlids": ["tcrm_saas_core.group_tcrm_tenant_manager"],
                "sequence": 70,
            },
            {
                "code": "tenant_admin",
                "name": "Kiracı — Admin (tam yetki)",
                "group_xmlids": ["tcrm_saas_core.group_tcrm_tenant_admin"],
                "sequence": 80,
            },
        ]

    def action_sync_org_access_grants(self):
        """Ensure grant rows exist for every curated feature."""
        Grant = self.env["tcrm.org.access.grant"]
        specs = self._tcrm_org_feature_specs()
        for user in self:
            existing = {g.code: g for g in user.org_access_grant_ids}
            for spec in specs:
                groups = self.env["res.groups"]
                for xmlid in spec["group_xmlids"]:
                    grp = self.env.ref(xmlid, raise_if_not_found=False)
                    if grp:
                        groups |= grp
                granted = bool(groups & user.group_ids)
                if spec["code"] in existing:
                    existing[spec["code"]].write(
                        {
                            "name": spec["name"],
                            "sequence": spec["sequence"],
                            "group_ids": [(6, 0, groups.ids)],
                            "granted": granted,
                        }
                    )
                else:
                    Grant.create(
                        {
                            "user_id": user.id,
                            "code": spec["code"],
                            "name": spec["name"],
                            "sequence": spec["sequence"],
                            "group_ids": [(6, 0, groups.ids)],
                            "granted": granted,
                        }
                    )
        return True
