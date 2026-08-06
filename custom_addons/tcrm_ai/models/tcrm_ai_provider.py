# Part of TCRM AI. See LICENSE for details.

from datetime import datetime, timedelta, timezone

from tcrm import _, api, fields, models


PROVIDER_CODES = [
    ('gemini', 'Google Gemini'),
    ('openai', 'OpenAI'),
    ('anthropic', 'Anthropic'),
    ('groq', 'Groq'),
    ('mistral', 'Mistral'),
    ('ollama', 'Ollama'),
]

KEY_STATUSES = [
    ('active', 'Active'),
    ('rate_limited', 'Rate Limited'),
    ('exhausted', 'Exhausted'),
    ('error', 'Error'),
    ('disabled', 'Disabled'),
]

HEALTH_STATUSES = [
    ('all_ok', 'All OK'),
    ('degraded', 'Degraded'),
    ('all_down', 'All Down'),
]


class TcrmAiProvider(models.Model):
    _name = 'tcrm.ai.provider'
    _description = 'TCRM AI Provider'
    _order = 'priority asc, id asc'

    name = fields.Char(string='Display Name', required=True)
    provider_code = fields.Selection(
        PROVIDER_CODES,
        string='Provider',
        required=True,
        index=True,
    )
    default_model = fields.Char(
        string='Default Model',
        required=True,
        help='e.g. gemini-2.0-flash, gpt-4o, claude-3-5-haiku-20241022',
    )
    priority = fields.Integer(
        string='Priority',
        default=10,
        help='Lower number = try first (1 = highest priority)',
    )
    active = fields.Boolean(string='Active', default=True)
    key_ids = fields.One2many(
        'tcrm.ai.key',
        'provider_id',
        string='API Keys',
        copy=False,
    )
    rpm_limit = fields.Integer(
        string='RPM Limit',
        default=0,
        help='Max requests per minute (0 = use provider default)',
    )
    rpd_limit = fields.Integer(
        string='RPD Limit',
        default=0,
        help='Max requests per day (0 = unlimited)',
    )
    tpm_limit = fields.Integer(
        string='TPM Limit',
        default=0,
        help='Max tokens per minute (0 = unlimited)',
    )
    active_key_count = fields.Integer(
        string='Active Keys',
        compute='_compute_active_key_count',
        store=False,
    )
    health_status = fields.Selection(
        HEALTH_STATUSES,
        string='Health',
        compute='_compute_health_status',
        store=False,
    )

    @api.depends('key_ids', 'key_ids.status')
    def _compute_active_key_count(self):
        for rec in self:
            rec.active_key_count = len(rec.key_ids.filtered(lambda k: k.status == 'active'))

    @api.depends('key_ids', 'key_ids.status')
    def _compute_health_status(self):
        for rec in self:
            keys = rec.key_ids.filtered(lambda k: k.active)
            if not keys:
                rec.health_status = 'all_down'
            elif all(k.status == 'active' for k in keys):
                rec.health_status = 'all_ok'
            else:
                rec.health_status = 'degraded'

    def action_reset_cooldowns(self):
        """Reset cooldowns for all keys of this provider."""
        self.ensure_one()
        self.key_ids.reset_cooldowns()
        return True

    def action_test_all_keys(self):
        """Test each key with a minimal request; show results as a notification."""
        self.ensure_one()
        results = self.env['tcrm.ai.engine']._test_provider_keys(self)
        if not results:
            message = _('No keys to test.')
            notif_type = 'warning'
        else:
            lines = []
            for name, ok, err in results:
                line = '• %s: %s' % (name, _('OK') if ok else _('Failed'))
                if err:
                    line = '%s — %s' % (line, err)
                lines.append(line)
            message = '\n'.join(lines)
            notif_type = 'success' if all(ok for _, ok, _ in results) else 'warning'
            # Groq provider OK must also unlock Settings/Asistan (same key path).
            if self.provider_code == 'groq' and any(ok for _, ok, _ in results):
                config = self.env['tcrm.ai.config'].sudo().get_config()
                try:
                    key = config._ensure_valid_groq_key()
                    if key and key.startswith('gsk_'):
                        vals = {
                            'last_connection_test': fields.Datetime.now(),
                            'last_connection_status': 'ok',
                            'last_safe_error': False,
                        }
                        if not config.ai_enabled:
                            vals['ai_enabled'] = True
                        config.sudo().write(vals)
                        from ..services import entitlement as entitlement_svc
                        entitlement_svc.set_entitlement_state(self.env, 'active')
                except Exception:
                    pass
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Key Test Results'),
                'message': message,
                'type': notif_type,
                'sticky': True,
            },
        }


class TcrmAiKey(models.Model):
    _name = 'tcrm.ai.key'
    _description = 'TCRM AI API Key Slot'
    _order = 'provider_id, sequence, id'

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        if 'name' not in fields_list or vals.get('name'):
            return vals
        provider_id = vals.get('provider_id') or self.env.context.get('default_provider_id')
        if provider_id:
            provider = self.env['tcrm.ai.provider'].browse(provider_id)
            count = len(provider.key_ids) if provider.exists() else 0
            vals['name'] = f'Key {count + 1}'
        return vals

    provider_id = fields.Many2one(
        'tcrm.ai.provider',
        string='Provider',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Label', required=True, help='e.g. Gemini Key 1, OpenAI Prod')
    api_key = fields.Char(
        string='API Key',
        required=True,
        help='API key value — use password widget in views; never log or expose.',
    )
    active = fields.Boolean(string='Enabled', default=True)
    status = fields.Selection(
        KEY_STATUSES,
        string='Status',
        default='active',
        required=True,
    )
    cooldown_until = fields.Datetime(
        string='Cooldown Until',
        help='When this key can be used again (UTC).',
    )
    rpm_count = fields.Integer(string='RPM Count', default=0)
    rpd_count = fields.Integer(string='RPD Count', default=0)
    tpm_used = fields.Integer(string='TPM Used', default=0)
    tpd_used = fields.Integer(string='TPD Used', default=0)
    rpm_window_start = fields.Datetime(
        string='RPM Window Start',
        help='Start of current minute window for RPM.',
    )
    rpd_date = fields.Date(
        string='RPD Date',
        help='Date of current RPD window.',
    )
    last_used = fields.Datetime(string='Last Used')
    last_error = fields.Text(string='Last Error')
    success_count = fields.Integer(string='Success Count', default=0)
    fail_count = fields.Integer(string='Consecutive Failures', default=0)
    total_calls = fields.Integer(string='Total Calls', default=0)

    key_display = fields.Char(
        string='Key (masked)',
        compute='_compute_key_display',
        help='Masked key for UI only; never the actual value.',
    )
    usage_display = fields.Char(
        string='Usage',
        compute='_compute_usage_display',
        help='e.g. 8/15 rpm for display.',
    )

    @api.depends('api_key')
    def _compute_key_display(self):
        for rec in self:
            if not rec.api_key or len(rec.api_key) < 8:
                rec.key_display = '****'
            else:
                rec.key_display = rec.api_key[:4] + '****' + rec.api_key[-4:]

    @api.depends('rpm_count', 'rpd_count', 'provider_id', 'provider_id.rpm_limit', 'provider_id.rpd_limit')
    def _compute_usage_display(self):
        for rec in self:
            if not rec.provider_id:
                rec.usage_display = ''
                continue
            rpm = rec.provider_id.rpm_limit or 0
            rpd = rec.provider_id.rpd_limit or 0
            parts = []
            if rpm:
                parts.append(f'{rec.rpm_count}/{rpm} rpm')
            if rpd:
                parts.append(f'{rec.rpd_count}/{rpd} rpd')
            rec.usage_display = ' '.join(parts) if parts else f'{rec.rpm_count} rpm'

    def is_available(self):
        """Returns True if this key can be used right now."""
        self.ensure_one()
        if not self.active or self.status == 'disabled':
            return False
        self.reset_if_cooldown_expired()
        return self.status == 'active'

    def reset_if_cooldown_expired(self):
        """If cooldown_until has passed, set status=active and clear cooldown."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for key in self:
            if key.cooldown_until and key.cooldown_until <= now:
                key.write({
                    'status': 'active',
                    'cooldown_until': False,
                })

    def mark_rate_limited(self):
        """Set status=rate_limited, cooldown_until = now + 60 seconds."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for key in self:
            key.write({
                'status': 'rate_limited',
                'cooldown_until': now + timedelta(seconds=60),
                'last_error': 'Rate limited (429)',
            })

    def mark_exhausted(self):
        """Set status=exhausted, cooldown_until = next midnight UTC."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        next_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        for key in self:
            key.write({
                'status': 'exhausted',
                'cooldown_until': next_midnight,
                'last_error': 'Daily/monthly quota exceeded',
            })

    def mark_error(self, error_message=None):
        """Increment fail_count. If fail_count >= 3: cooldown 5 minutes."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for key in self:
            new_fail = key.fail_count + 1
            cooldown_until = False
            status = key.status
            if new_fail >= 3:
                cooldown_until = now + timedelta(minutes=5)
                status = 'error'
            key.write({
                'fail_count': new_fail,
                'last_error': error_message or key.last_error,
                'cooldown_until': cooldown_until or key.cooldown_until,
                'status': status,
            })

    def mark_success(self, tokens_used=0):
        """Reset fail_count, increment counters, update last_used."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        today = now.date()
        for key in self:
            # Reset RPM/RPD windows if we're in a new minute/day
            rpm_start = key.rpm_window_start
            rpd_date = key.rpd_date
            new_rpm_start = rpm_start
            new_rpd_date = rpd_date
            if not rpm_start or (now - rpm_start).total_seconds() >= 60:
                new_rpm_start = now
            if rpd_date != today:
                new_rpd_date = today
            new_rpm = (key.rpm_count + 1) if new_rpm_start == rpm_start else 1
            new_rpd = (key.rpd_count + 1) if new_rpd_date == rpd_date else 1
            new_tpm = (key.tpm_used + tokens_used) if new_rpm_start == rpm_start else tokens_used
            new_tpd = (key.tpd_used + tokens_used) if new_rpd_date == rpd_date else tokens_used
            key.write({
                'fail_count': 0,
                'status': 'active',
                'cooldown_until': False,
                'last_used': now,
                'success_count': key.success_count + 1,
                'total_calls': key.total_calls + 1,
                'rpm_count': new_rpm,
                'rpd_count': new_rpd,
                'tpm_used': new_tpm,
                'tpd_used': new_tpd,
                'rpm_window_start': new_rpm_start,
                'rpd_date': new_rpd_date,
            })

    def reset_cooldowns(self):
        """Clear cooldown and set status to active (admin override)."""
        self.write({
            'cooldown_until': False,
            'status': 'active',
            'fail_count': 0,
        })
