# Part of TCRM AI Research. See LICENSE for details.

from tcrm import api, fields, models
from tcrm.exceptions import AccessError, ValidationError


class TcrmAiWorkspace(models.Model):
    _name = 'tcrm.ai.workspace'
    _description = 'AI Research Workspace'
    _order = 'name, id'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    owner_id = fields.Many2one(
        'res.users',
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )
    member_ids = fields.Many2many(
        'res.users',
        'tcrm_ai_workspace_user_rel',
        'workspace_id',
        'user_id',
        string='Members',
    )
    ragflow_dataset_id = fields.Char(string='RAGFlow Dataset ID', index=True)
    ragflow_assistant_id = fields.Char(string='RAGFlow Assistant / Chat ID', index=True)
    description = fields.Text()
    default_language = fields.Selection(
        [('tr', 'Turkish'), ('en', 'English')],
        default='tr',
        required=True,
    )
    allow_web_research = fields.Boolean(default=False)
    conversation_ids = fields.One2many('tcrm.ai.conversation', 'workspace_id', string='Conversations')
    document_ids = fields.One2many('tcrm.ai.document', 'workspace_id', string='Documents')
    conversation_count = fields.Integer(compute='_compute_counts')
    document_count = fields.Integer(compute='_compute_counts')

    _sql_constraints = [
        (
            'tcrm_ai_workspace_name_company_uniq',
            'unique(name, company_id)',
            'Workspace name must be unique per company.',
        ),
    ]

    @api.depends('conversation_ids', 'document_ids')
    def _compute_counts(self):
        for rec in self:
            rec.conversation_count = len(rec.conversation_ids)
            rec.document_count = len(rec.document_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault('company_id', self.env.company.id)
            vals.setdefault('owner_id', self.env.user.id)
            members = vals.get('member_ids')
            owner_id = vals.get('owner_id') or self.env.user.id
            if not members:
                vals['member_ids'] = [(6, 0, [owner_id])]
        return super().create(vals_list)

    def _user_is_member(self):
        self.ensure_one()
        user = self.env.user
        if user.has_group('tcrm_ai_research.group_ai_research_admin') or user.has_group('base.group_system'):
            return True
        if user.has_group('tcrm_ai_research.group_ai_research_manager'):
            return self.company_id in user.company_ids
        return user == self.owner_id or user in self.member_ids

    def _check_membership(self):
        for rec in self:
            if not rec._user_is_member():
                raise AccessError(self.env._('You are not allowed to access this workspace.'))

    @api.constrains('company_id', 'owner_id')
    def _check_owner_company(self):
        for rec in self:
            if rec.owner_id.company_id and rec.company_id not in rec.owner_id.company_ids:
                raise ValidationError(
                    self.env._('Workspace owner must belong to the workspace company.')
                )
