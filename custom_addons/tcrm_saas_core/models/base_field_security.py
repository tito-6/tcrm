from tcrm import _, models
from tcrm.exceptions import AccessError


class BaseFieldSecurity(models.AbstractModel):
    _inherit = "base"

    def _check_field_access(self, field, operation):
        super()._check_field_access(field, operation)

        if self.env.su or self.env.user.has_group("base.group_system"):
            return

        user = self.env.user
        permission_sets = user.permission_set_ids.filtered(
            lambda s: s.active and s.company_id in self.env.companies
        )
        if not permission_sets:
            return

        line = self.env["tcrm.permission.set.line"].sudo().search(
            [
                ("permission_set_id", "in", permission_sets.ids),
                ("model_id.model", "=", self._name),
                ("field_id.name", "=", field.name),
            ],
            limit=1,
        )
        if not line:
            return

        if operation == "read" and not line.can_read:
            raise AccessError(
                _("You do not have permission to read field '%(field)s' on %(model)s.", field=field.string, model=self._description)
            )
        if operation == "write" and not line.can_write:
            raise AccessError(
                _("You do not have permission to edit field '%(field)s' on %(model)s.", field=field.string, model=self._description)
            )
