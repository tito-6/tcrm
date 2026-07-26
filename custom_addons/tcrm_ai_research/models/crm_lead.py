# Part of TCRM AI Research. See LICENSE for details.

from tcrm import fields, models
from tcrm.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    ai_conversation_count = fields.Integer(compute='_compute_ai_conversation_count')

    def _compute_ai_conversation_count(self):
        Conversation = self.env['tcrm.ai.conversation']
        for lead in self:
            lead.ai_conversation_count = Conversation.search_count([
                '|',
                ('lead_id', '=', lead.id),
                '&', ('res_model', '=', 'crm.lead'), ('res_id', '=', lead.id),
            ])

    def action_open_ai_research(self):
        self.ensure_one()
        self.check_access('read')
        workspace = self.env['tcrm.ai.workspace'].search([
            ('company_id', '=', self.env.company.id),
            ('active', '=', True),
        ], limit=1)
        if not workspace:
            raise UserError(
                self.env._('Create an AI Research workspace for this company first.')
            )
        workspace._check_membership()
        return {
            'type': 'ir.actions.client',
            'tag': 'tcrm_ai_research.assistant',
            'name': self.env._('AI Research'),
            'context': {
                'company_id': self.env.company.id,
                'user_id': self.env.user.id,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'lead_id': self.id,
                'res_model': 'crm.lead',
                'res_id': self.id,
                'record_name': self.display_name,
                'workspace_id': workspace.id,
            },
        }
