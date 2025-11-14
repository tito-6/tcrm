from odoo import models, fields


class MetaLeadMapping(models.Model):
    _name = 'meta.lead.mapping'
    _description = 'Meta Lead Assignment Mapping'

    name = fields.Char(required=True, help="Short label for this rule")
    active = fields.Boolean(default=True)

    page_id = fields.Char(string='Meta Page ID', help="Facebook Page ID (optional)")
    form_id = fields.Char(string='Meta Form ID', help="Facebook Lead Form ID (optional)")

    team_id = fields.Many2one('crm.team', string='Sales Team')
    user_id = fields.Many2one('res.users', string='Salesperson')

    note = fields.Text()
