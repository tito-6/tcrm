# Part of TCRM AI. See LICENSE for details.

from tcrm import api, models, fields

from .tcrm_ai_config import GEMINI_MODELS


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gemini_api_key = fields.Char(
        string='Gemini API Key',
        help='Google AI Studio API key for TCRM AI (Discuss bot and Ask TCRM AI).',
    )
    gemini_model = fields.Selection(
        GEMINI_MODELS,
        string='Gemini Model',
        default='gemini-2.0-flash',
        help='Model used for TCRM AI answers. See https://ai.google.dev/gemini-api/docs/models.',
    )
    ai_base_url = fields.Char(
        string='Local AI / RAG proxy URL',
        help='Base URL for Ollama/RAG proxy (e.g. http://45.9.191.119:8000). Used by AI chat and vector sync.',
    )
    ai_request_timeout = fields.Integer(
        string='Request timeout (seconds)',
        default=45,
        help='Timeout for each AI API request. Increase for slow or distant providers (e.g. Ollama).',
    )
    ai_provider_summary = fields.Char(
        string='AI providers',
        compute='_compute_ai_provider_summary',
        help='Summary of configured AI providers and keys (read-only).',
    )
    ai_health_status = fields.Selection(
        [
            ('all_ok', 'All OK'),
            ('degraded', 'Degraded'),
            ('all_down', 'All Down'),
            ('none', 'No providers'),
        ],
        string='AI health',
        compute='_compute_ai_provider_summary',
    )

    @api.depends()
    def _compute_ai_provider_summary(self):
        for rec in self:
            try:
                providers = rec.env['tcrm.ai.provider'].sudo().search([('active', '=', True)])
                active_providers = providers.filtered(lambda p: (p.active_key_count or 0) > 0)
                total_keys = sum(len(p.key_ids.filtered(lambda k: k.active)) for p in active_providers)
                if not active_providers:
                    rec.ai_provider_summary = 'No active providers or keys'
                    rec.ai_health_status = 'none'
                else:
                    rec.ai_provider_summary = f'{len(active_providers)} provider(s), {total_keys} key(s)'
                    statuses = set(active_providers.mapped('health_status'))
                    if 'all_down' in statuses and len(statuses) == 1:
                        rec.ai_health_status = 'all_down'
                    elif 'all_ok' in statuses and 'all_down' not in statuses and 'degraded' not in statuses:
                        rec.ai_health_status = 'all_ok'
                    else:
                        rec.ai_health_status = 'degraded'
            except Exception:
                rec.ai_provider_summary = 'Configure providers below'
                rec.ai_health_status = 'none'

    @api.model
    def get_values(self):
        res = super().get_values()
        config = self.env['tcrm.ai.config'].sudo().get_config()
        ICP = self.env['ir.config_parameter'].sudo()
        res.update(
            gemini_api_key=config.gemini_api_key or '',
            gemini_model=config.gemini_model or 'gemini-2.0-flash',
            ai_base_url=ICP.get_param('tcrm.ai_base_url', '') or '',
            ai_request_timeout=int(ICP.get_param('tcrm.ai_request_timeout', '45') or 45),
        )
        return res

    def set_values(self):
        super().set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        config = self.env['tcrm.ai.config'].sudo().get_config()
        config.write({
            'gemini_api_key': self.gemini_api_key or '',
            'gemini_model': self.gemini_model or 'gemini-2.0-flash',
        })
        url = (self.ai_base_url or '').strip().rstrip('/')
        ICP.set_param('tcrm.ai_base_url', url)
        ICP.set_param('tcrm.ai_request_timeout', str(max(5, min(120, self.ai_request_timeout or 45))))
