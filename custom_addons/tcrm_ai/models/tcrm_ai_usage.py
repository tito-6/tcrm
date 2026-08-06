# Part of TCRM AI. See LICENSE for details.

from tcrm import models, fields, api

from ..services.constants import GROQ_COST_PER_M_TOKENS


class TcrmAiUsage(models.Model):
    _name = 'tcrm.ai.usage'
    _description = 'TCRM AI Usage Record'
    _order = 'id desc'

    name = fields.Char(default='AI Request')
    database_name = fields.Char(string='Tenant Database', default=lambda self: self.env.cr.dbname, index=True, readonly=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, index=True)
    provider = fields.Char(default='groq')
    model = fields.Char()
    conversation_id = fields.Many2one('tcrm.ai.assistant.conversation', ondelete='set null', index=True)
    prompt_tokens = fields.Integer(default=0)
    completion_tokens = fields.Integer(default=0)
    total_tokens = fields.Integer(default=0)
    duration_ms = fields.Integer(string='Request Duration (ms)', default=0)
    tool_count = fields.Integer(default=0)
    tools_used = fields.Char()
    success = fields.Boolean(default=True)
    safe_error_code = fields.Char()
    correlation_id = fields.Char(string='Correlation ID', index=True)
    estimated_cost = fields.Float(string='Estimated Cost (USD)', digits=(12, 6), default=0.0)
    in_flight = fields.Boolean(default=False, index=True)

    @api.model
    def start_request(self, conversation=None):
        return self.create({
            'name': 'AI Request',
            'conversation_id': conversation.id if conversation else False,
            'in_flight': True,
            'success': False,
        })

    def finish(self, *, usage=None, duration_ms=0, tools=None, success=True, error_code=None, provider='groq', model=None):
        usage = usage or {}
        prompt = int(usage.get('prompt_tokens') or 0)
        completion = int(usage.get('completion_tokens') or 0)
        total = int(usage.get('total_tokens') or (prompt + completion))
        tools = tools or []
        cost = (total / 1_000_000.0) * GROQ_COST_PER_M_TOKENS
        self.write({
            'prompt_tokens': prompt,
            'completion_tokens': completion,
            'total_tokens': total,
            'duration_ms': int(duration_ms or 0),
            'tool_count': len(tools),
            'tools_used': ','.join(tools)[:500],
            'success': bool(success),
            'safe_error_code': error_code or False,
            'estimated_cost': cost,
            'provider': provider or 'groq',
            'model': model or False,
            'in_flight': False,
        })
        return self
