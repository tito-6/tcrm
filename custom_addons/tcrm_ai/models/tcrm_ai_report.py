# Part of TCRM AI. See LICENSE for details.

from tcrm import models, fields, _


class TcrmAiReport(models.Model):
    _name = 'tcrm.ai.report'
    _description = 'TCRM AI Saved Report'
    _order = 'id desc'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, index=True)
    period_days = fields.Integer(string='Report Period (days)')
    payload_json = fields.Text(string='Verified Payload')
    currency_id = fields.Many2one('res.currency')
    record_count = fields.Integer()
    data_source = fields.Char(default='TCRM ORM tools')
    generation_date = fields.Datetime(default=fields.Datetime.now)
