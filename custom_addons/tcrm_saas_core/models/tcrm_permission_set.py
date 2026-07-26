from tcrm import _, api, fields, models
from tcrm.exceptions import ValidationError


class TcrmPermissionSet(models.Model):
    _name = "tcrm.permission.set"
    _description = "TCRM Permission Set"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    active = fields.Boolean(default=True)
    line_ids = fields.One2many("tcrm.permission.set.line", "permission_set_id", string="Field Permissions")
    user_ids = fields.Many2many("res.users", "tcrm_permission_set_user_rel", "permission_set_id", "user_id", string="Users")


class TcrmPermissionSetLine(models.Model):
    _name = "tcrm.permission.set.line"
    _description = "TCRM Permission Set Line"
    _order = "model_id, field_id"

    permission_set_id = fields.Many2one("tcrm.permission.set", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="permission_set_id.company_id", store=True, readonly=True, index=True)
    model_id = fields.Many2one("ir.model", required=True, ondelete="cascade", string="Model")
    field_id = fields.Many2one(
        "ir.model.fields",
        required=True,
        ondelete="cascade",
        string="Field",
        domain="[('model_id', '=', model_id)]",
    )
    can_read = fields.Boolean(default=True)
    can_write = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "tcrm_permission_line_unique",
            "unique(permission_set_id, field_id)",
            "A field can only appear once in a permission set.",
        ),
    ]

    @api.constrains("model_id", "field_id")
    def _check_model_field_match(self):
        for rec in self:
            if rec.field_id.model_id != rec.model_id:
                raise ValidationError(_("Selected field does not belong to the selected model."))
