# Part of TCRM AI Research. See LICENSE for details.

import os

from tcrm import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tcrm_ai_research_base_url = fields.Char(
        string='RAGFlow Base URL',
        config_parameter='tcrm_ai_research.base_url',
        help='Base URL of the self-hosted RAGFlow instance (e.g. https://ragflow.example.com). '
             'May be overridden by RAGFLOW_BASE_URL.',
    )
    tcrm_ai_research_api_key = fields.Char(
        string='RAGFlow API Key',
        config_parameter='tcrm_ai_research.api_key',
        help='API key used for server-to-server calls. Never exposed to the browser. '
             'May be overridden by RAGFLOW_API_KEY.',
    )
    tcrm_ai_research_default_dataset_id = fields.Char(
        string='Default Dataset ID',
        config_parameter='tcrm_ai_research.default_dataset_id',
        help='Default RAGFlow dataset / knowledge-base ID. '
             'May be overridden by RAGFLOW_DEFAULT_DATASET_ID.',
    )
    tcrm_ai_research_default_assistant_id = fields.Char(
        string='Default Assistant / Chat ID',
        config_parameter='tcrm_ai_research.default_assistant_id',
        help='Default RAGFlow chat assistant ID. '
             'May be overridden by RAGFLOW_DEFAULT_ASSISTANT_ID.',
    )
    tcrm_ai_research_timeout = fields.Integer(
        string='Request Timeout (seconds)',
        config_parameter='tcrm_ai_research.timeout',
        default=60,
    )
    tcrm_ai_research_max_upload_size_mb = fields.Integer(
        string='Maximum Upload Size (MB)',
        config_parameter='tcrm_ai_research.max_upload_size_mb',
        default=25,
    )
    tcrm_ai_research_default_language = fields.Selection(
        [('tr', 'Turkish'), ('en', 'English')],
        string='Default Language',
        config_parameter='tcrm_ai_research.default_language',
        default='tr',
    )
    tcrm_ai_research_enable_web_research = fields.Boolean(
        string='Enable Web Research',
        config_parameter='tcrm_ai_research.enable_web_research',
        default=False,
    )
    tcrm_ai_research_enable_streaming = fields.Boolean(
        string='Enable Streaming',
        config_parameter='tcrm_ai_research.enable_streaming',
        default=True,
    )
    tcrm_ai_research_allowed_extensions = fields.Char(
        string='Allowed File Extensions',
        config_parameter='tcrm_ai_research.allowed_extensions',
        default='pdf,txt,doc,docx,md,csv,xlsx,pptx',
        help='Comma-separated list of allowed upload extensions.',
    )
    tcrm_ai_research_env_override_hint = fields.Char(
        string='Environment Override',
        compute='_compute_env_override_hint',
        help='Shows whether sensitive values are overridden by environment variables.',
    )

    @api.depends_context('uid')
    def _compute_env_override_hint(self):
        flags = []
        if os.environ.get('RAGFLOW_BASE_URL'):
            flags.append('BASE_URL')
        if os.environ.get('RAGFLOW_API_KEY'):
            flags.append('API_KEY')
        if os.environ.get('RAGFLOW_DEFAULT_DATASET_ID'):
            flags.append('DATASET_ID')
        if os.environ.get('RAGFLOW_DEFAULT_ASSISTANT_ID'):
            flags.append('ASSISTANT_ID')
        if os.environ.get('RAGFLOW_TIMEOUT'):
            flags.append('TIMEOUT')
        hint = ', '.join(flags) if flags else self.env._('None')
        for rec in self:
            rec.tcrm_ai_research_env_override_hint = hint
