# Part of TCRM AI. See LICENSE for details.

import logging

from tcrm import models, fields, api, _
from tcrm.exceptions import AccessError, UserError, ValidationError

from ..services.constants import (
    APPROVED_GROQ_MODELS,
    APPROVED_PROVIDERS,
    DEFAULT_DAILY_REQUEST_LIMIT,
    DEFAULT_DAILY_TOKEN_LIMIT,
    DEFAULT_GROQ_MODEL,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_MONTHLY_SEARCH_QUOTA,
    DEFAULT_MONTHLY_USAGE_LIMIT,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_RETENTION_DAYS,
    DEFAULT_RPM_LIMIT,
    DEFAULT_SEARCH_MAX_RESULTS,
    DEFAULT_SEARCH_TIMEOUT,
    ENTITLEMENT_STATES,
    GROQ_BASE_URL,
    SAFE_ERROR_CODES,
    SEARCH_PROVIDERS,
)
from ..services.crypto import (
    decrypt_secret,
    encrypt_secret,
    looks_like_masked_secret,
    mask_api_key,
    normalize_api_key,
)
from ..services import entitlement as entitlement_svc
from ..services.groq_provider import GroqProviderError, GroqProviderService, validate_model

_logger = logging.getLogger(__name__)

# Legacy Gemini constants kept for migration of old rows.
GEMINI_MODELS = [
    ('gemini-2.0-flash', 'Gemini 2.0 Flash'),
    ('gemini-2.5-flash', 'Gemini 2.5 Flash'),
    ('gemini-2.5-pro', 'Gemini 2.5 Pro'),
]
DEPRECATED_GEMINI_TO_CURRENT = {
    'gemini-1.5-flash-8b': 'gemini-2.0-flash',
    'gemini-1.5-flash': 'gemini-2.0-flash',
    'gemini-1.5-pro': 'gemini-2.0-flash',
}
FALLBACK_ORDER = ['gemini-2.0-flash', 'gemini-2.5-flash']

REASONING_LEVELS = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
]

CONNECTION_STATUSES = [
    ('unknown', 'Bilinmiyor'),
    ('ok', 'Başarılı'),
    ('error', 'Hata'),
]


class TcrmAiConfig(models.Model):
    _name = 'tcrm.ai.config'
    _description = 'TCRM AI Configuration'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        ondelete='cascade',
        required=True,
        index=True,
    )

    # ── Core ───────────────────────────────────────────────────────
    ai_enabled = fields.Boolean(string='AI Enabled', default=False)
    provider = fields.Selection(APPROVED_PROVIDERS, string='Provider', default='groq', required=True)
    base_url = fields.Char(string='Base URL', default=GROQ_BASE_URL, required=True)
    model = fields.Selection(
        APPROVED_GROQ_MODELS,
        string='Model',
        default=DEFAULT_GROQ_MODEL,
        required=True,
    )

    api_key_encrypted = fields.Char(string='API Key (stored)', copy=False, groups='tcrm_ai.group_tcrm_ai_admin')
    api_key_input = fields.Char(
        string='API Key',
        store=False,
        help='Enter a Groq key (gsk_...). Never returned after save.',
    )
    api_key_masked = fields.Char(string='API Key (masked)', compute='_compute_key_status')
    has_api_key = fields.Boolean(string='Key Configured', compute='_compute_key_status')

    default_language = fields.Selection(
        [('tr', 'Türkçe'), ('en', 'English')],
        string='Default Language',
        default='tr',
        required=True,
    )
    default_reasoning_level = fields.Selection(REASONING_LEVELS, string='Default Reasoning Level', default='medium')
    max_output_tokens = fields.Integer(string='Maximum Output Tokens', default=DEFAULT_MAX_OUTPUT_TOKENS)
    request_timeout = fields.Integer(string='Request Timeout', default=DEFAULT_REQUEST_TIMEOUT)
    max_tool_calls = fields.Integer(string='Maximum Tool Calls', default=DEFAULT_MAX_TOOL_CALLS)

    daily_request_limit = fields.Integer(string='Daily Request Limit', default=DEFAULT_DAILY_REQUEST_LIMIT)
    daily_token_limit = fields.Integer(string='Daily Token Limit', default=DEFAULT_DAILY_TOKEN_LIMIT)
    monthly_usage_limit = fields.Integer(string='Monthly Usage Limit', default=DEFAULT_MONTHLY_USAGE_LIMIT)
    rpm_limit = fields.Integer(string='Requests Per Minute Limit', default=DEFAULT_RPM_LIMIT)

    allow_crm_data = fields.Boolean(string='Allow CRM Data', default=True)
    allow_sales_data = fields.Boolean(string='Allow Sales Data', default=True)
    allow_property_data = fields.Boolean(string='Allow Property Data', default=True)
    allow_payment_data = fields.Boolean(string='Allow Payment Data', default=True)
    allow_reports = fields.Boolean(string='Allow Reports', default=True)
    allow_internet_research = fields.Boolean(
        string='Gerçek Zamanlı İnternet Araştırmasına İzin Ver',
        default=True,
    )

    # Public internet research provider (credentials never sent to chat UI).
    search_provider = fields.Selection(SEARCH_PROVIDERS, string='Search Provider', default='duckduckgo')
    search_api_key_encrypted = fields.Char(string='Search API Key (stored)', copy=False, groups='tcrm_ai.group_tcrm_ai_admin')
    search_api_key_input = fields.Char(string='Search API Key', store=False)
    search_enabled = fields.Boolean(string='Search Enabled', default=True)
    search_timeout = fields.Integer(string='Search Timeout', default=DEFAULT_SEARCH_TIMEOUT)
    search_max_results = fields.Integer(string='Maximum Search Results', default=DEFAULT_SEARCH_MAX_RESULTS)
    search_allowed_domains = fields.Char(string='Allowed Domains', help='Comma-separated allowlist (optional)')
    search_blocked_domains = fields.Char(string='Blocked Domains', help='Comma-separated blocklist')
    search_monthly_quota = fields.Integer(string='Monthly Search Quota', default=DEFAULT_MONTHLY_SEARCH_QUOTA)

    save_conversation_history = fields.Boolean(string='Save Conversation History', default=True)
    conversation_retention_days = fields.Integer(string='Conversation Retention Days', default=DEFAULT_RETENTION_DAYS)
    mask_personal_data = fields.Boolean(string='Mask Personal Data', default=True)

    last_connection_test = fields.Datetime(string='Last Connection Test', readonly=True)
    last_connection_status = fields.Selection(CONNECTION_STATUSES, string='Last Connection Status', default='unknown', readonly=True)
    last_safe_error = fields.Char(string='Last Safe Error', readonly=True)
    last_connection_latency_ms = fields.Integer(string='Last Latency (ms)', readonly=True)

    entitlement_status = fields.Selection(
        ENTITLEMENT_STATES,
        string='Entitlement Status',
        compute='_compute_entitlement_status',
    )
    module_installed = fields.Boolean(string='Module Installed', default=True, readonly=True)
    status_summary = fields.Char(string='Status Summary', compute='_compute_status_summary')

    # Legacy Gemini fields (kept so upgrades do not wipe old rows)
    gemini_api_key = fields.Char(string='Gemini API Key (legacy)', groups='base.group_system')
    gemini_model = fields.Selection(GEMINI_MODELS, string='Gemini Model (legacy)', default='gemini-2.0-flash')
    ai_base_url = fields.Char(string='Local AI / RAG proxy URL (legacy)')
    temperature = fields.Float(string='Temperature', default=0.3)
    max_tokens = fields.Integer(string='Max tokens (legacy)', default=DEFAULT_MAX_OUTPUT_TOKENS)
    provider_summary = fields.Char(string='AI providers', compute='_compute_provider_summary')

    _sql_constraints = [
        ('tcrm_ai_config_company_uniq', 'unique(company_id)', 'Only one TCRM AI config per company.'),
    ]

    @api.depends('company_id', 'provider', 'model')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = 'TCRM AI — %s' % (rec.company_id.name or _('Settings'))

    @api.depends('api_key_encrypted')
    def _compute_key_status(self):
        for rec in self:
            plain = normalize_api_key(
                decrypt_secret(rec.env, rec.api_key_encrypted) if rec.api_key_encrypted else ''
            )
            # Masked / non-ASCII leftovers must not count as a configured key.
            rec.has_api_key = bool(plain)
            rec.api_key_masked = mask_api_key(plain) if plain else ''

    def _compute_entitlement_status(self):
        for rec in self:
            rec.entitlement_status = entitlement_svc.get_entitlement_state(rec.env)

    @api.depends(
        'ai_enabled', 'has_api_key', 'last_connection_status', 'provider', 'model',
        'entitlement_status',
    )
    def _compute_status_summary(self):
        for rec in self:
            parts = [
                _('Entitlement: %s') % dict(ENTITLEMENT_STATES).get(rec.entitlement_status, rec.entitlement_status),
                _('Provider: %s') % (rec.provider or '-'),
                _('Model: %s') % (rec.model or '-'),
                _('Key: %s') % (_('var') if rec.has_api_key else _('yok')),
                _('Enabled: %s') % (_('evet') if rec.ai_enabled else _('hayır')),
                _('Connection: %s') % (rec.last_connection_status or 'unknown'),
            ]
            rec.status_summary = ' | '.join(parts)

    @api.depends()
    def _compute_provider_summary(self):
        for rec in self:
            if rec.has_api_key and rec.provider:
                rec.provider_summary = '%s / %s' % (rec.provider, rec.model)
            else:
                rec.provider_summary = _('Yapılandırma gerekli')

    @api.model
    def get_config(self, company=None):
        company = company or self.env.company
        configs = self.sudo().search([('company_id', '=', company.id)], order='id asc')
        if not configs:
            config = self.sudo().create({
                'company_id': company.id,
                'ai_enabled': False,
                'provider': 'groq',
                'base_url': GROQ_BASE_URL,
                'model': DEFAULT_GROQ_MODEL,
                'allow_payment_data': True,
                'allow_internet_research': True,
            })
            # Empty disabled config for newly provisioned tenants
            if not entitlement_svc.is_master_database(self.env):
                state = entitlement_svc.get_entitlement_state(self.env)
                if state in ('granted', 'unavailable'):
                    entitlement_svc.set_entitlement_state(self.env, 'config_required' if state != 'unavailable' else state)
            return config
        config = configs[0]
        # Keep a single row per company (older installs may have duplicates).
        extras = configs[1:]
        if extras:
            # Prefer a row that already has a usable key / enabled flag.
            ranked = configs.sorted(
                key=lambda c: (
                    1 if c.ai_enabled else 0,
                    1 if c.api_key_encrypted else 0,
                    1 if c.last_connection_status == 'ok' else 0,
                    -c.id,
                ),
                reverse=True,
            )
            config = ranked[0]
            (configs - config).unlink()
        return config

    def _set_runtime_state(self, state):
        entitlement_svc.set_entitlement_state(self.env, state)

    def _get_provider_groq_api_key(self):
        """Return plaintext key from the Groq provider key pool, if any."""
        if 'tcrm.ai.key' not in self.env:
            return ''
        Key = self.env['tcrm.ai.key'].sudo()
        slots = Key.search([
            ('provider_id.provider_code', '=', 'groq'),
            ('provider_id.active', '=', True),
            ('active', '=', True),
            ('status', 'in', ('active', 'rate_limited')),
        ], order='sequence asc, id asc')
        for slot in slots:
            key = normalize_api_key(slot.api_key)
            if key and key.startswith('gsk_'):
                return key
        return ''

    def _ensure_valid_groq_key(self):
        """
        Heal settings key from the Groq provider pool when the stored key is
        missing or not a real Groq key (e.g. truncated sk_... instead of gsk_...).
        """
        self.ensure_one()
        if self.provider and self.provider != 'groq':
            return self._get_plaintext_api_key()
        current = self._get_plaintext_api_key()
        if current.startswith('gsk_'):
            return current
        provider_key = self._get_provider_groq_api_key()
        if not provider_key:
            return current
        self.sudo().write({
            'api_key_encrypted': encrypt_secret(self.env, provider_key),
            'provider': 'groq',
            'base_url': self.base_url or GROQ_BASE_URL,
        })
        _logger.info(
            'TCRM AI: synced Groq provider key into tcrm.ai.config id=%s db=%s',
            self.id, self.env.cr.dbname,
        )
        return provider_key

    def _get_plaintext_api_key(self):
        self.ensure_one()
        return normalize_api_key(decrypt_secret(self.env, self.api_key_encrypted))

    def _require_ai_admin(self):
        if not (
            self.env.user.has_group('tcrm_ai.group_tcrm_ai_admin')
            or self.env.user.has_group('base.group_system')
        ):
            raise AccessError(_('TCRM AI ayarları yalnızca AI yöneticileri tarafından değiştirilebilir.'))

    @api.model_create_multi
    def create(self, vals_list):
        records = self.browse()
        to_create = []
        for vals in vals_list:
            vals = dict(vals)
            self._normalize_vals(vals)
            company_id = vals.get('company_id') or self.env.company.id
            existing = self.sudo().search([('company_id', '=', company_id)], limit=1)
            if existing:
                # Never create a second config for the same company.
                writable = {
                    k: v for k, v in vals.items()
                    if k not in ('company_id', 'id') and v not in (None, False, '')
                }
                if writable:
                    try:
                        existing.write(writable)
                    except Exception:
                        pass
                records |= existing
            else:
                vals['company_id'] = company_id
                to_create.append(vals)
        if to_create:
            records |= super().create(to_create)
        return records

    def write(self, vals):
        self._require_ai_admin()
        vals = dict(vals)
        self._normalize_vals(vals)
        return super().write(vals)

    def _normalize_vals(self, vals):
        if 'model' in vals and vals['model']:
            try:
                vals['model'] = validate_model(vals['model'])
            except GroqProviderError as exc:
                raise ValidationError(exc.safe_message) from exc
        if 'provider' in vals and vals['provider'] and vals['provider'] not in dict(APPROVED_PROVIDERS):
            raise ValidationError(_('Desteklenmeyen sağlayıcı.'))
        if 'base_url' in vals and vals.get('base_url'):
            vals['base_url'] = vals['base_url'].strip().rstrip('/')
        if 'api_key_input' in vals:
            raw = (vals.pop('api_key_input') or '').strip()
            if raw:
                if looks_like_masked_secret(raw):
                    # Ignore password-widget / masked re-posts; keep existing secret.
                    raw = ''
                else:
                    raw = normalize_api_key(raw)
                    if not raw:
                        raise ValidationError(_(
                            'API anahtarı geçersiz. Yalnızca gerçek Groq anahtarını (gsk_...) yapıştırın; '
                            'maskelenmiş değeri kaydetmeyin.'
                        ))
                    provider = vals.get('provider') or (self[:1].provider if self else 'groq')
                    if provider == 'groq' and not raw.startswith('gsk_'):
                        raise ValidationError(_(
                            'API anahtarı geçersiz. Groq anahtarı gsk_ ile başlamalıdır. '
                            'Sağlayıcılar ekranındaki anahtarı buraya kopyalamayın; '
                            'console.groq.com üzerinden tam anahtarı yapıştırın.'
                        ))
                    vals['api_key_encrypted'] = encrypt_secret(self.env, raw)
                    # New key must be re-tested before chat unlocks.
                    vals.setdefault('last_connection_status', 'unknown')
                    vals.setdefault('last_safe_error', False)
        if 'search_api_key_input' in vals:
            raw = (vals.pop('search_api_key_input') or '').strip()
            if raw and not looks_like_masked_secret(raw):
                vals['search_api_key_encrypted'] = encrypt_secret(self.env, normalize_api_key(raw))
        # Never allow writing plaintext api key fields from RPC
        for banned in ('api_key', 'gemini_api_key', 'search_api_key'):
            if banned in vals and vals[banned]:
                # migrate legacy gemini into encrypted store only if explicitly provided by admin form
                if banned == 'gemini_api_key':
                    continue
                vals.pop(banned, None)
        if 'max_output_tokens' in vals:
            vals['max_output_tokens'] = max(64, min(8192, int(vals['max_output_tokens'] or DEFAULT_MAX_OUTPUT_TOKENS)))
        if 'request_timeout' in vals:
            vals['request_timeout'] = max(5, min(180, int(vals['request_timeout'] or DEFAULT_REQUEST_TIMEOUT)))
        if 'daily_request_limit' in vals:
            vals['daily_request_limit'] = max(1, min(2000, int(vals['daily_request_limit'] or DEFAULT_DAILY_REQUEST_LIMIT)))
        if 'daily_token_limit' in vals:
            vals['daily_token_limit'] = max(1000, min(2000000, int(vals['daily_token_limit'] or DEFAULT_DAILY_TOKEN_LIMIT)))
        if 'rpm_limit' in vals:
            vals['rpm_limit'] = max(1, min(60, int(vals['rpm_limit'] or DEFAULT_RPM_LIMIT)))
        if 'max_tool_calls' in vals:
            vals['max_tool_calls'] = max(1, min(24, int(vals['max_tool_calls'] or DEFAULT_MAX_TOOL_CALLS)))

    def read(self, fields=None, load='_classic_read'):
        rows = super().read(fields=fields, load=load)
        sensitive = {
            'api_key_encrypted', 'api_key_input', 'gemini_api_key', 'api_key',
            'search_api_key_encrypted', 'search_api_key_input', 'search_api_key',
        }
        for row in rows:
            for key in list(row):
                if key in sensitive:
                    if key in ('api_key_encrypted', 'search_api_key_encrypted'):
                        row[key] = bool(row[key])
                    else:
                        row[key] = False
        return rows

    def action_save_settings(self):
        self._require_ai_admin()
        self.ensure_one()
        # Form already wrote values; refresh entitlement state
        if self.has_api_key and self.ai_enabled:
            if entitlement_svc.get_entitlement_state(self.env) in ('granted', 'config_required', 'connection_error', 'active'):
                self._set_runtime_state('active' if self.last_connection_status == 'ok' else 'config_required')
        elif entitlement_svc.get_entitlement_state(self.env) != 'unavailable':
            self._set_runtime_state('config_required')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('TCRM AI'),
                'message': _('Ayarlar kaydedildi.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_test_connection(self):
        self._require_ai_admin()
        self.ensure_one()
        ok_ent, code = entitlement_svc.entitlement_allows_requests(self.env)
        if not ok_ent:
            msg = SAFE_ERROR_CODES.get(code or 'entitlement_denied')
            self.write({
                'last_connection_test': fields.Datetime.now(),
                'last_connection_status': 'error',
                'last_safe_error': msg,
            })
            raise UserError(msg)
        # Prefer a healed Groq key (settings may hold a truncated sk_... copy).
        key = self._ensure_valid_groq_key()
        if not key:
            # Clear corrupt / masked leftovers so the UI stops pretending a key exists.
            if self.api_key_encrypted:
                self.sudo().write({'api_key_encrypted': False})
            msg = _(
                'Geçerli bir API anahtarı yok. Maskelenmiş değer kaydedilmiş olabilir — '
                'lütfen gerçek Groq anahtarını (gsk_...) yeniden yapıştırıp kaydedin.'
            )
            self.write({
                'last_connection_test': fields.Datetime.now(),
                'last_connection_status': 'error',
                'last_safe_error': msg,
            })
            raise UserError(msg)
        try:
            service = GroqProviderService(
                api_key=key,
                base_url=self.base_url or GROQ_BASE_URL,
                model=self.model or DEFAULT_GROQ_MODEL,
                timeout=min(30, self.request_timeout or 45),
                max_retries=1,
            )
            result = service.test_connection()
            self.write({
                'last_connection_test': fields.Datetime.now(),
                'last_connection_status': 'ok',
                'last_safe_error': False,
                'last_connection_latency_ms': result.get('latency_ms') or 0,
            })
            # Connection OK unlocks chat when AI is enabled; otherwise mark ready.
            if self.ai_enabled:
                self._set_runtime_state('active')
            elif entitlement_svc.get_entitlement_state(self.env) in (
                'config_required', 'connection_error', 'granted', 'active',
            ):
                # Key works — leave enabled flag to the admin, but clear hard block state.
                self._set_runtime_state('config_required')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('TCRM AI'),
                    'message': result.get('message') or _('Groq bağlantısı başarılı.'),
                    'type': 'success',
                    'sticky': False,
                },
            }
        except UnicodeEncodeError as exc:
            msg = SAFE_ERROR_CODES['invalid_api_key']
            self.write({
                'last_connection_test': fields.Datetime.now(),
                'last_connection_status': 'error',
                'last_safe_error': msg,
                'api_key_encrypted': False,
            })
            raise UserError(_(
                'API anahtarı geçersiz karakterler içeriyor. '
                'Lütfen gerçek Groq anahtarını yeniden girin.'
            )) from exc
        except GroqProviderError as exc:
            self.write({
                'last_connection_test': fields.Datetime.now(),
                'last_connection_status': 'error',
                'last_safe_error': exc.safe_message,
            })
            if entitlement_svc.get_entitlement_state(self.env) not in ('unavailable', 'suspended'):
                self._set_runtime_state('connection_error')
            # Store diagnostics for admins only (no secrets)
            self.env['ir.logging'].sudo().create({
                'name': 'tcrm_ai.connection_test',
                'type': 'server',
                'dbname': self.env.cr.dbname,
                'level': 'WARNING',
                'message': 'connection_test code=%s diag=%s' % (exc.code, (exc.diagnostics or '')[:500]),
                'path': 'tcrm_ai',
                'func': 'action_test_connection',
                'line': '0',
            }) if 'ir.logging' in self.env else None
            raise UserError(exc.safe_message) from exc

    def action_change_key(self):
        self._require_ai_admin()
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Anahtarı Değiştir'),
            'res_model': 'tcrm.ai.key.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_config_id': self.id},
        }

    def action_delete_key(self):
        self._require_ai_admin()
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Anahtarı Sil'),
            'res_model': 'tcrm.ai.key.delete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_config_id': self.id},
        }

    def action_disable_ai(self):
        self._require_ai_admin()
        self.write({'ai_enabled': False})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('TCRM AI'),
                'message': _('AI’ı Devre Dışı Bırakıldı.'),
                'type': 'warning',
                'sticky': False,
            },
        }

    def _get_plaintext_search_api_key(self):
        self.ensure_one()
        if not self.search_api_key_encrypted:
            return ''
        return normalize_api_key(decrypt_secret(self.env, self.search_api_key_encrypted) or '')

    @api.model
    def get_chat_status(self):
        """Minimal status for chat / floating UI — no provider, model, key, or tokens."""
        config = self.get_config()
        block = entitlement_svc.chat_block_reason(self.env)
        return {
            'chat_enabled': not bool(block) and bool(config.ai_enabled) and bool(config.has_api_key),
            'chat_disabled_reason': block or '',
            'configured': bool(config.has_api_key),
            'ai_enabled': bool(config.ai_enabled),
            'allow_internet_research': bool(config.allow_internet_research and config.search_enabled),
            'default_language': config.default_language,
            'title': 'TCRM AI Asistan',
        }

    @api.model
    def get_public_status(self):
        """Admin-safe status — never includes plaintext secrets. Chat UI must use get_chat_status."""
        config = self.get_config()
        block = entitlement_svc.chat_block_reason(self.env)
        from ..services.rate_limit import usage_dashboard
        usage = {}
        try:
            usage = usage_dashboard(self.env)
        except Exception:
            usage = {}
        return {
            'entitlement_status': config.entitlement_status,
            'module_installed': True,
            'provider': config.provider,
            'model': config.model,
            'base_url': config.base_url,
            'configured': bool(config.has_api_key),
            'api_key_masked': config.api_key_masked or '',
            'ai_enabled': bool(config.ai_enabled),
            'last_connection_status': config.last_connection_status,
            'last_connection_test': fields.Datetime.to_string(config.last_connection_test) if config.last_connection_test else '',
            'last_safe_error': config.last_safe_error or '',
            'chat_disabled_reason': block,
            'chat_enabled': not bool(block) and bool(config.ai_enabled) and bool(config.has_api_key),
            'limits': {
                'daily_request_limit': config.daily_request_limit,
                'daily_token_limit': config.daily_token_limit,
                'monthly_usage_limit': config.monthly_usage_limit,
                'rpm_limit': config.rpm_limit,
            },
            'usage': usage,
            'default_language': config.default_language,
            'approved_models': [m[0] for m in APPROVED_GROQ_MODELS],
            'approved_providers': [p[0] for p in APPROVED_PROVIDERS],
            'search_provider': config.search_provider,
            'search_enabled': bool(config.search_enabled),
            'allow_internet_research': bool(config.allow_internet_research),
        }

    @api.model
    def save_settings_rpc(self, values):
        """RPC-safe settings save. Strips secrets from response."""
        self = self.sudo() if self.env.user.has_group('base.group_system') else self
        if not (
            self.env.user.has_group('tcrm_ai.group_tcrm_ai_admin')
            or self.env.user.has_group('base.group_system')
        ):
            raise AccessError(_('Access denied'))
        config = self.get_config()
        allowed = {
            'ai_enabled', 'provider', 'base_url', 'model', 'api_key_input',
            'default_language', 'default_reasoning_level', 'max_output_tokens',
            'request_timeout', 'max_tool_calls', 'daily_request_limit',
            'daily_token_limit', 'monthly_usage_limit', 'rpm_limit',
            'allow_crm_data', 'allow_sales_data', 'allow_property_data',
            'allow_payment_data', 'allow_reports', 'allow_internet_research',
            'save_conversation_history', 'conversation_retention_days',
            'mask_personal_data', 'temperature',
            'search_provider', 'search_api_key_input', 'search_enabled',
            'search_timeout', 'search_max_results', 'search_allowed_domains',
            'search_blocked_domains', 'search_monthly_quota',
        }
        vals = {k: values[k] for k in (values or {}) if k in allowed}
        search_key = vals.pop('search_api_key_input', None)
        config.write(vals)
        if search_key and not looks_like_masked_secret(search_key):
            config.write({'search_api_key_encrypted': encrypt_secret(self.env, normalize_api_key(search_key))})
        config.action_save_settings()
        return config.get_public_status()

    def clear_api_key(self):
        self._require_ai_admin()
        self.write({'api_key_encrypted': False, 'ai_enabled': False})
        if entitlement_svc.get_entitlement_state(self.env) not in ('unavailable', 'suspended'):
            self._set_runtime_state('config_required')
        return True

    @api.model
    def cron_purge_old_conversations(self):
        for config in self.search([]):
            days = config.conversation_retention_days or DEFAULT_RETENTION_DAYS
            if days <= 0:
                continue
            from datetime import timedelta
            cutoff = fields.Datetime.now() - timedelta(days=days)
            old = self.env['tcrm.ai.assistant.conversation'].sudo().search([
                ('company_id', '=', config.company_id.id),
                ('write_date', '<', cutoff),
            ])
            old.unlink()
