# Part of TCRM AI Research. See LICENSE for details.

from tcrm import api, fields, models
from tcrm.exceptions import AccessError, UserError, ValidationError


class TcrmAiConversation(models.Model):
    _name = 'tcrm.ai.conversation'
    _description = 'AI Research Conversation'
    _order = 'last_activity_at desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, default='New Research', tracking=True)
    workspace_id = fields.Many2one(
        'tcrm.ai.workspace',
        required=True,
        ondelete='cascade',
        index=True,
    )
    user_id = fields.Many2one(
        'res.users',
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )
    company_id = fields.Many2one(
        related='workspace_id.company_id',
        store=True,
        index=True,
    )
    partner_id = fields.Many2one('res.partner', index=True, ondelete='set null')
    lead_id = fields.Many2one('crm.lead', index=True, ondelete='set null')
    res_model = fields.Char(index=True)
    res_id = fields.Integer(index=True)
    record_name = fields.Char()
    ragflow_session_id = fields.Char(index=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('archived', 'Archived'),
        ],
        default='active',
        required=True,
        index=True,
    )
    language = fields.Selection(
        [('tr', 'Turkish'), ('en', 'English')],
        default='tr',
    )
    allow_web_research = fields.Boolean(default=False)
    internal_documents_only = fields.Boolean(default=True)
    ai_message_ids = fields.One2many('tcrm.ai.message', 'conversation_id', string='Messages')
    document_ids = fields.Many2many(
        'tcrm.ai.document',
        'tcrm_ai_conversation_document_rel',
        'conversation_id',
        'document_id',
        string='Documents',
    )
    last_activity_at = fields.Datetime(default=fields.Datetime.now, index=True)
    message_count = fields.Integer(compute='_compute_message_count')

    @api.depends('ai_message_ids')
    def _compute_message_count(self):
        for rec in self:
            rec.message_count = len(rec.ai_message_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault('user_id', self.env.user.id)
            vals.setdefault('last_activity_at', fields.Datetime.now())
            if vals.get('workspace_id'):
                workspace = self.env['tcrm.ai.workspace'].browse(vals['workspace_id'])
                workspace._check_membership()
                vals.setdefault('language', workspace.default_language)
                vals.setdefault('allow_web_research', workspace.allow_web_research)
            if vals.get('name') == 'New Research' or not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('tcrm.ai.conversation') or 'New Research'
        return super().create(vals_list)

    @api.constrains('partner_id', 'lead_id', 'company_id')
    def _check_company_consistency(self):
        for rec in self:
            if rec.partner_id and rec.partner_id.company_id and rec.partner_id.company_id != rec.company_id:
                if rec.partner_id.company_id not in self.env.companies:
                    raise ValidationError(self.env._('Partner company mismatch.'))
            if rec.lead_id and rec.lead_id.company_id and rec.lead_id.company_id != rec.company_id:
                raise ValidationError(self.env._('Lead company must match conversation company.'))

    def _touch_activity(self):
        self.write({'last_activity_at': fields.Datetime.now()})

    def action_open_assistant(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'tcrm_ai_research.assistant',
            'name': self.env._('AI Research'),
            'context': {
                'conversation_id': self.id,
                'workspace_id': self.workspace_id.id,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'lead_id': self.lead_id.id if self.lead_id else False,
                'res_model': self.res_model,
                'res_id': self.res_id,
                'record_name': self.record_name or self.display_name,
            },
        }

    def ask_question(self, question: str, language: str | None = None, document_ids=None):
        """Send a question through the research provider and store messages."""
        self.ensure_one()
        self.workspace_id._check_membership()
        if not question or not str(question).strip():
            raise UserError(self.env._('Please enter a question.'))

        from ..services.context_builder import ContextBuilder
        from ..services.exceptions import RagflowError
        from ..services import ragflow_client as ragflow_client_mod

        lang = language or self.language or 'tr'
        context = ContextBuilder(self.env).build(
            res_model=self.res_model,
            res_id=self.res_id,
            partner_id=self.partner_id.id if self.partner_id else None,
            lead_id=self.lead_id.id if self.lead_id else None,
        )

        if document_ids:
            docs = self.env['tcrm.ai.document'].browse(document_ids).exists()
            for doc in docs:
                doc.check_access('read')
                if doc.workspace_id != self.workspace_id:
                    raise AccessError(self.env._('Document is outside this workspace.'))
            self.document_ids = [(6, 0, docs.ids)]

        user_msg = self.env['tcrm.ai.message'].create({
            'conversation_id': self.id,
            'role': 'user',
            'content': question.strip(),
            'language': lang,
            'status': 'done',
        })

        assistant_msg = self.env['tcrm.ai.message'].create({
            'conversation_id': self.id,
            'role': 'assistant',
            'content': '',
            'language': lang,
            'status': 'pending',
        })

        prompt = question.strip()
        if context.get('prompt_text'):
            if lang == 'tr':
                prompt = (
                    f"{context['prompt_text']}\n\n"
                    f"Lütfen Türkçe yanıt ver.\n\nSoru: {question.strip()}"
                )
            else:
                prompt = (
                    f"{context['prompt_text']}\n\n"
                    f"Please answer in English.\n\nQuestion: {question.strip()}"
                )

        correlation_id = f'conv-{self.id}-{assistant_msg.id}'
        try:
            provider = ragflow_client_mod.get_research_provider(self.env, correlation_id=correlation_id)
            chat_id = self.workspace_id.ragflow_assistant_id
            session_id = self.ragflow_session_id
            if chat_id and not session_id:
                session = provider.create_session(chat_id, name=self.name or 'TCRM session')
                session_id = session.get('id')
                self.ragflow_session_id = session_id

            result = provider.ask(
                prompt,
                chat_id=chat_id or None,
                session_id=session_id or None,
                stream=False,
            )
            if result.get('session_id') and not self.ragflow_session_id:
                self.ragflow_session_id = result['session_id']

            assistant_msg.write({
                'content': result.get('answer') or '',
                'status': 'done',
                'ragflow_message_id': result.get('message_id') or False,
            })
            assistant_msg._create_citations(result.get('citations') or [])
        except RagflowError as exc:
            assistant_msg.write({
                'status': 'error',
                'error_message': str(exc)[:500],
                'content': self.env._('The research request failed. Please try again.'),
            })
        self._touch_activity()
        return {
            'user_message_id': user_msg.id,
            'assistant_message_id': assistant_msg.id,
            'conversation_id': self.id,
        }
