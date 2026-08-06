# Part of TCRM AI. See LICENSE for details.

from tcrm import models, fields


class TcrmAiAudit(models.Model):
    _name = 'tcrm.ai.audit'
    _description = 'TCRM AI Tool Audit'
    _order = 'id desc'

    user_id = fields.Many2one('res.users', required=True, index=True)
    company_id = fields.Many2one('res.company', required=True, index=True)
    tool_name = fields.Char(required=True, index=True)
    arguments_safe = fields.Text()
    success = fields.Boolean(default=True)
    detail = fields.Char()
