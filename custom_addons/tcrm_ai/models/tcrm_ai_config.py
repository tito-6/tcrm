# Part of TCRM AI. See LICENSE for details.
# Model IDs from https://ai.google.dev/gemini-api/docs/models (Google AI for Developers)
# Only include models that support generateContent on v1beta. Deprecated models removed.

from tcrm import models, fields, api

# Current Gemini API model IDs (v1beta). Deprecated (e.g. gemini-1.5-flash-8b, gemini-1.5-flash) removed.
GEMINI_MODELS = [
    # Gemini 3 (preview) — https://ai.google.dev/gemini-api/docs/models
    ('gemini-3.1-pro-preview', 'Gemini 3.1 Pro (Preview)'),
    ('gemini-3-flash-preview', 'Gemini 3 Flash (Preview)'),
    ('gemini-3.1-flash-lite-preview', 'Gemini 3.1 Flash Lite (Preview)'),
    # Gemini 2.5 (GA)
    ('gemini-2.5-pro', 'Gemini 2.5 Pro'),
    ('gemini-2.5-flash', 'Gemini 2.5 Flash'),
    ('gemini-2.5-flash-lite', 'Gemini 2.5 Flash Lite'),
    # Gemini 2.0 (stable)
    ('gemini-2.0-flash', 'Gemini 2.0 Flash'),
]

# Map deprecated/removed model IDs to a current model (used when config has old value).
DEPRECATED_GEMINI_TO_CURRENT = {
    'gemini-1.5-flash-8b': 'gemini-2.0-flash',
    'gemini-1.5-flash': 'gemini-2.0-flash',
    'gemini-1.5-pro': 'gemini-2.0-flash',
    'gemini-1.0-pro': 'gemini-2.0-flash',
    'gemini-pro': 'gemini-2.0-flash',
}

# Fallback order when rate limit (429) or quota is hit. Use only current model IDs.
# https://ai.google.dev/gemini-api/docs/rate-limits
FALLBACK_ORDER = [
    'gemini-3.1-flash-lite-preview',
    'gemini-2.5-flash-lite',
    'gemini-2.5-flash',
    'gemini-3-flash-preview',
    'gemini-2.0-flash',
    'gemini-2.5-pro',
    'gemini-3.1-pro-preview',
]


class TcrmAiConfig(models.Model):
    _name = 'tcrm.ai.config'
    _description = 'TCRM AI Configuration'
    _rec_name = 'id'

    gemini_api_key = fields.Char(
        string='Gemini API Key',
        default='',
        help='Get a free key at https://aistudio.google.com/apikey — leave empty until you add yours.',
    )
    gemini_model = fields.Selection(
        GEMINI_MODELS,
        string='Gemini Model',
        default='gemini-2.0-flash',
        required=True,
        help='Which Gemini model to use for TCRM AI. See https://ai.google.dev/gemini-api/docs/models.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        ondelete='cascade',
    )
    ai_base_url = fields.Char(
        string='Local AI / RAG proxy URL',
        help='Base URL for Ollama or RAG proxy. Synced with Settings; used by AI chat and vector sync.',
    )
    request_timeout = fields.Integer(
        string='Request timeout (seconds)',
        default=45,
        help='Timeout per AI API request. Increase for slow or distant providers.',
    )
    temperature = fields.Float(
        string='Temperature',
        default=0.7,
        help='Model creativity (0 = deterministic, 1 = more random).',
    )
    max_tokens = fields.Integer(
        string='Max tokens per reply',
        default=4096,
        help='Maximum tokens generated per AI reply.',
    )
    provider_summary = fields.Char(
        string='AI providers',
        compute='_compute_provider_summary',
        help='Summary of active providers and keys (read-only).',
    )

    @api.depends()
    def _compute_provider_summary(self):
        for rec in self:
            providers = rec.env['tcrm.ai.provider'].sudo().search([('active', '=', True)])
            active_providers = providers.filtered(lambda p: p.active_key_count > 0)
            total_keys = sum(len(p.key_ids.filtered(lambda k: k.active)) for p in active_providers)
            if not active_providers:
                rec.provider_summary = 'No active providers or keys — add keys in AI Providers or use Gemini fallback above.'
            else:
                rec.provider_summary = f'{len(active_providers)} provider(s), {total_keys} key(s)'

    def _table_exists(self, table_name):
        """True if table exists in current schema."""
        self.env.cr.execute("""
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = current_schema() AND table_name = %s
            LIMIT 1
        """, (table_name,))
        return bool(self.env.cr.fetchone())

    def _ensure_tcrm_ai_key_table(self):
        """Create tcrm_ai_key table if missing (e.g. module was not fully upgraded)."""
        if self._table_exists('tcrm_ai_key'):
            return
        cr = self.env.cr
        cr.execute("""
            CREATE TABLE tcrm_ai_key (
                id SERIAL PRIMARY KEY,
                provider_id INTEGER NOT NULL REFERENCES tcrm_ai_provider(id) ON DELETE CASCADE,
                sequence INTEGER DEFAULT 10,
                name VARCHAR NOT NULL,
                api_key VARCHAR NOT NULL,
                active BOOLEAN DEFAULT true,
                status VARCHAR(32) DEFAULT 'active',
                cooldown_until TIMESTAMP,
                rpm_count INTEGER DEFAULT 0,
                rpd_count INTEGER DEFAULT 0,
                tpm_used INTEGER DEFAULT 0,
                tpd_used INTEGER DEFAULT 0,
                rpm_window_start TIMESTAMP,
                rpd_date DATE,
                last_used TIMESTAMP,
                last_error TEXT,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                total_calls INTEGER DEFAULT 0,
                create_uid INTEGER,
                create_date TIMESTAMP,
                write_uid INTEGER,
                write_date TIMESTAMP
            )
        """)
        cr.execute("CREATE INDEX IF NOT EXISTS tcrm_ai_key_provider_id_index ON tcrm_ai_key (provider_id)")

    def _has_new_ai_config_columns(self):
        """True if DB table has the new AI config columns (after module upgrade)."""
        self.env.cr.execute("""
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = current_schema() AND table_name = 'tcrm_ai_config'
            AND column_name = 'ai_base_url'
            LIMIT 1
        """)
        return bool(self.env.cr.fetchone())

    def _add_new_ai_config_columns_if_missing(self):
        """Add new AI config columns if they don't exist (allows running without module upgrade)."""
        if self._has_new_ai_config_columns():
            return
        cr = self.env.cr
        for col, sql in [
            ('ai_base_url', "ALTER TABLE tcrm_ai_config ADD COLUMN ai_base_url VARCHAR DEFAULT ''"),
            ('request_timeout', 'ALTER TABLE tcrm_ai_config ADD COLUMN request_timeout INTEGER DEFAULT 45'),
            ('temperature', 'ALTER TABLE tcrm_ai_config ADD COLUMN temperature DOUBLE PRECISION DEFAULT 0.7'),
            ('max_tokens', 'ALTER TABLE tcrm_ai_config ADD COLUMN max_tokens INTEGER DEFAULT 4096'),
        ]:
            try:
                cr.execute(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = current_schema() AND table_name = 'tcrm_ai_config' AND column_name = %s",
                    (col,),
                )
                if cr.fetchone():
                    continue
                cr.execute(sql)
            except Exception:
                pass

    @api.model
    def get_config(self, company=None):
        self._add_new_ai_config_columns_if_missing()
        self._ensure_tcrm_ai_key_table()
        company = company or self.env.company
        config = self.search([('company_id', '=', company.id)], limit=1)
        has_new_cols = self._has_new_ai_config_columns()
        if not config:
            vals = {
                'company_id': company.id,
                'gemini_api_key': '',
                'gemini_model': 'gemini-2.0-flash',
            }
            if has_new_cols:
                ICP = self.env['ir.config_parameter'].sudo()
                vals['ai_base_url'] = ICP.get_param('tcrm.ai_base_url', '') or ''
                vals['request_timeout'] = int(ICP.get_param('tcrm.ai_request_timeout', '45') or 45)
            config = self.create(vals)
        else:
            if has_new_cols:
                ICP = self.env['ir.config_parameter'].sudo()
                updates = {}
                if not config.ai_base_url and ICP.get_param('tcrm.ai_base_url'):
                    updates['ai_base_url'] = (ICP.get_param('tcrm.ai_base_url') or '').strip().rstrip('/')
                if (config.request_timeout or 0) == 0 and ICP.get_param('tcrm.ai_request_timeout'):
                    updates['request_timeout'] = int(ICP.get_param('tcrm.ai_request_timeout', '45') or 45)
                if updates:
                    config.write(updates)
        return config

    def _sync_to_icp(self, vals):
        ICP = self.env['ir.config_parameter'].sudo()
        if 'ai_base_url' in vals:
            url = (vals.get('ai_base_url') or '').strip().rstrip('/')
            ICP.set_param('tcrm.ai_base_url', url)
        if 'request_timeout' in vals:
            t = vals.get('request_timeout') or 45
            ICP.set_param('tcrm.ai_request_timeout', str(max(5, min(120, t))))

    @api.model_create_multi
    def create(self, vals_list):
        configs = super().create(vals_list)
        for config, vals in zip(configs, vals_list):
            config._sync_to_icp(vals)
        return configs

    def write(self, vals):
        res = super().write(vals)
        if vals:
            self._sync_to_icp(vals)
        return res
