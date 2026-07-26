from tcrm import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    permission_set_ids = fields.Many2many(
        'tcrm.permission.set',
        'tcrm_permission_set_user_rel',
        'user_id',
        'permission_set_id',
        string='Permission Sets',
        domain="[('company_id', '=', company_id)]",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            company_id = vals.get('company_id')
            company_ids = vals.get('company_ids')
            if company_id and not company_ids:
                vals['company_ids'] = [(6, 0, [company_id])]
            elif company_id and company_ids:
                companies = set()
                for cmd in company_ids:
                    if isinstance(cmd, (list, tuple)) and len(cmd) >= 3 and cmd[0] == 6:
                        companies.update(cmd[2] or [])
                if company_id not in companies:
                    companies.add(company_id)
                    vals['company_ids'] = [(6, 0, list(companies))]
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'company_id' in vals:
            for user in self:
                if user.company_id and user.company_id not in user.company_ids:
                    user.company_ids = [(4, user.company_id.id)]
        return res
