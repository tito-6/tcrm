# Part of TCRM AI. See LICENSE for details.

from tcrm import models, fields, api, _


class TcrmAiAssistantConversation(models.Model):
    _name = 'tcrm.ai.assistant.conversation'
    _description = 'TCRM AI Assistant Conversation'
    _order = 'write_date desc, id desc'

    name = fields.Char(string='Title', required=True, default=lambda self: _('Yeni Sohbet'))
    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, index=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    active = fields.Boolean(default=True)
    message_ids = fields.One2many('tcrm.ai.assistant.message', 'conversation_id', string='Messages')
    message_count = fields.Integer(compute='_compute_message_count')
    total_tokens = fields.Integer(string='Total Tokens', default=0)
    last_message_date = fields.Datetime(string='Last Message')
    language = fields.Selection([('tr', 'Türkçe'), ('en', 'English')], default='tr')
    source_type = fields.Selection(
        [
            ('assistant', 'Full Assistant'),
            ('floating', 'Floating Assistant'),
            ('discuss', 'Discuss'),
            ('html_editor', 'HTML Editor / Native AI'),
            ('crm', 'CRM'),
            ('report', 'Report'),
            ('api', 'API'),
        ],
        string='Source',
        default='assistant',
        index=True,
    )
    tenant_db = fields.Char(
        string='Tenant Database',
        default=lambda self: self.env.cr.dbname,
        readonly=True,
        index=True,
    )

    @api.depends('message_ids')
    def _compute_message_count(self):
        for rec in self:
            rec.message_count = len(rec.message_ids)

    def action_delete_conversation(self):
        self.unlink()
        return True


class TcrmAiAssistantMessage(models.Model):
    _name = 'tcrm.ai.assistant.message'
    _description = 'TCRM AI Assistant Message'
    _order = 'id asc'

    conversation_id = fields.Many2one('tcrm.ai.assistant.conversation', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='conversation_id.company_id', store=True, index=True)
    user_id = fields.Many2one(related='conversation_id.user_id', store=True, index=True)
    role = fields.Selection(
        [('system', 'System'), ('user', 'User'), ('assistant', 'Assistant'), ('tool', 'Tool')],
        required=True,
    )
    content = fields.Text(string='Safe Content')
    tool_calls_json = fields.Text(string='Tool Calls')
    tool_name = fields.Char(string='Tool Name')
    referenced_records = fields.Text(string='Referenced Records')
    prompt_tokens = fields.Integer(default=0)
    completion_tokens = fields.Integer(default=0)
    total_tokens = fields.Integer(default=0)
    provider = fields.Char()
    model = fields.Char()
    correlation_id = fields.Char(string='Correlation ID', index=True)
