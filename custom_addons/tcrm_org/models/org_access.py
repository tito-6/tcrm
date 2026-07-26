# -*- coding: utf-8 -*-
from tcrm import api, fields, models


class TcrmOrgAccessGrant(models.Model):
    _name = "tcrm.org.access.grant"
    _description = "Organizasyon Ekran / Modül Erişimi"
    _order = "sequence, name"

    user_id = fields.Many2one(
        "res.users",
        string="Kullanıcı",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="user_id.company_id",
        store=True,
        readonly=True,
    )
    code = fields.Char(required=True, index=True)
    name = fields.Char(string="Modül / Özellik", required=True)
    sequence = fields.Integer(default=10)
    granted = fields.Boolean(string="Erişim", default=False)
    group_ids = fields.Many2many(
        "res.groups",
        "tcrm_org_access_grant_group_rel",
        "grant_id",
        "group_id",
        string="Bağlı Gruplar",
    )
    menu_ids = fields.Many2many(
        "ir.ui.menu",
        "tcrm_org_access_grant_menu_rel",
        "grant_id",
        "menu_id",
        string="Menüler / Ekranlar",
        help="İsteğe bağlı: ek menü görünürlüğü (gruplara ek olarak).",
    )

    _sql_constraints = [
        (
            "tcrm_org_access_user_code_uniq",
            "unique(user_id, code)",
            "Bu özellik için kullanıcıda tek erişim satırı olabilir.",
        ),
    ]

    def write(self, vals):
        res = super().write(vals)
        if "granted" in vals or "group_ids" in vals or "menu_ids" in vals:
            self._apply_grants()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._apply_grants()
        return records

    def _apply_grants(self):
        """Add/remove security groups and optional menu visibility."""
        for grant in self:
            user = grant.user_id.sudo()
            if not user or user._is_superuser():
                continue
            groups = grant.group_ids
            if grant.granted:
                to_add = groups - user.group_ids
                if to_add:
                    user.write({"group_ids": [(4, g.id) for g in to_add]})
            else:
                to_remove = groups & user.group_ids
                # Do not strip base.group_user
                base_user = self.env.ref("base.group_user")
                to_remove = to_remove - base_user
                if to_remove:
                    user.write({"group_ids": [(3, g.id) for g in to_remove]})
            # Menu-level: attach a dedicated per-user shadow group is heavy;
            # instead ensure granted menus include the user's groups already.
            if grant.menu_ids and grant.granted:
                for menu in grant.menu_ids.sudo():
                    # Allow access by ensuring at least one of user's groups is on the menu
                    if not (menu.group_ids & user.group_ids) and groups:
                        menu.write({"group_ids": [(4, g.id) for g in groups[:1]]})


class TcrmOrgAccessWizard(models.TransientModel):
    _name = "tcrm.org.access.wizard"
    _description = "Kullanıcı Erişim Yönetimi"

    user_id = fields.Many2one("res.users", required=True, string="Kullanıcı")
    line_ids = fields.One2many(
        "tcrm.org.access.wizard.line",
        "wizard_id",
        string="Erişimler",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        user_id = res.get("user_id") or self.env.context.get("default_user_id")
        if user_id and "line_ids" in fields_list:
            user = self.env["res.users"].browse(user_id)
            user.action_sync_org_access_grants()
            lines = []
            for grant in user.org_access_grant_ids.sorted("sequence"):
                lines.append(
                    (
                        0,
                        0,
                        {
                            "grant_id": grant.id,
                            "name": grant.name,
                            "code": grant.code,
                            "granted": grant.granted,
                        },
                    )
                )
            res["line_ids"] = lines
        return res

    def action_apply(self):
        self.ensure_one()
        for line in self.line_ids:
            if line.grant_id:
                line.grant_id.granted = line.granted
        return {"type": "ir.actions.act_window_close"}


class TcrmOrgAccessWizardLine(models.TransientModel):
    _name = "tcrm.org.access.wizard.line"
    _description = "Kullanıcı Erişim Satırı"
    _order = "id"

    wizard_id = fields.Many2one("tcrm.org.access.wizard", required=True, ondelete="cascade")
    grant_id = fields.Many2one("tcrm.org.access.grant", string="Erişim Kaydı")
    name = fields.Char(string="Modül / Özellik", readonly=True)
    code = fields.Char(readonly=True)
    granted = fields.Boolean(string="Verildi")
