# -*- coding: utf-8 -*-
"""Tenant-local Santral (voice) provider configuration."""
from __future__ import annotations

import logging

from tcrm import api, fields, models, _
from tcrm.exceptions import AccessError, UserError, ValidationError

from ..services.crypto import decrypt_secret, encrypt_secret, mask_secret, mask_sid
from ..services.providers import get_provider

_logger = logging.getLogger(__name__)

SECRET_PLACEHOLDER = '********'


class TcrmCallProviderConfig(models.Model):
    _name = 'tcrm.call.provider.config'
    _description = 'Santral Provider Configuration'
    _rec_name = 'display_name'
    _order = 'company_id'

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company,
        index=True, ondelete='cascade',
    )
    display_name = fields.Char(compute='_compute_display_name', store=False)
    provider = fields.Selection([('twilio', 'Twilio')], default='twilio', required=True)
    enabled = fields.Boolean(string='Enabled', default=False)

    account_sid = fields.Char(string='Account SID', groups='tcrm_call_center.group_santral_admin')
    api_key_sid = fields.Char(string='API Key SID', groups='tcrm_call_center.group_santral_admin')
    api_key_secret_encrypted = fields.Char(string='API Key Secret (stored)', groups='tcrm_call_center.group_santral_admin', copy=False)
    auth_token_encrypted = fields.Char(string='Auth Token (stored)', groups='tcrm_call_center.group_santral_admin', copy=False)

    # Write-only UI fields — never persisted in plaintext.
    api_key_secret = fields.Char(string='API Key Secret', store=False, inverse='_inverse_api_key_secret')
    auth_token = fields.Char(string='Auth Token', store=False, inverse='_inverse_auth_token')

    twiml_app_sid = fields.Char(string='TwiML App SID', groups='tcrm_call_center.group_santral_admin')
    verified_caller_id = fields.Char(string='Verified Caller ID', groups='tcrm_call_center.group_santral_admin')
    public_callback_base_url = fields.Char(
        string='Public Callback Base URL',
        help='Approved public HTTPS base, e.g. https://tcrm.online or https://tenant.tcrm.online',
        groups='tcrm_call_center.group_santral_admin',
    )
    twilio_edge = fields.Selection(
        [('roaming', 'Roaming (Default)'), ('frankfurt', 'Frankfurt'), ('dublin', 'Dublin')],
        string='Twilio Edge Location',
        default='roaming',
        groups='tcrm_call_center.group_santral_admin'
    )

    recording_enabled = fields.Boolean(string='Recording Enabled', default=True)
    dual_channel_recording = fields.Boolean(string='Dual Channel Recording', default=True)
    recording_announcement_enabled = fields.Boolean(string='Recording Announcement Enabled', default=True)
    recording_announcement_text = fields.Text(
        string='Recording Announcement Text',
        default='Bu görüşme kalite ve eğitim amacıyla kaydedilebilir.',
    )
    recording_retention_days = fields.Integer(string='Recording Retention Days', default=90)
    allow_recording_download = fields.Boolean(string='Allow Recording Download', default=False)
    recording_storage = fields.Selection(
        [('proxy_twilio', 'Retain in Twilio + proxy playback'),
         ('attachment', 'Download into protected tenant attachment')],
        string='Recording Storage',
        default='proxy_twilio',
        required=True,
    )

    last_connection_test = fields.Datetime(string='Last Connection Test', readonly=True)
    last_connection_status = fields.Selection(
        [('unknown', 'Unknown'), ('ok', 'OK'), ('error', 'Error'), ('missing', 'Yapılandırma gerekli')],
        default='missing', readonly=True,
    )
    last_error = fields.Char(string='Last Error', readonly=True)
    legal_warning = fields.Html(
        string='Legal Notice',
        compute='_compute_legal_warning',
        sanitize=False,
    )

    account_sid_masked = fields.Char(compute='_compute_masks')
    api_key_sid_masked = fields.Char(compute='_compute_masks')
    twiml_app_sid_masked = fields.Char(compute='_compute_masks')
    verified_caller_id_masked = fields.Char(compute='_compute_masks')
    has_api_key_secret = fields.Boolean(compute='_compute_masks')
    has_auth_token = fields.Boolean(compute='_compute_masks')
    is_configured = fields.Boolean(compute='_compute_is_configured', store=True)

    _sql_constraints = [
        ('company_uniq', 'unique(company_id)', 'Each company may have only one Santral configuration.'),
    ]

    @api.depends('company_id', 'provider', 'enabled')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s / %s' % (
                rec.company_id.display_name or 'Company',
                dict(rec._fields['provider'].selection).get(rec.provider, rec.provider),
            )

    def _compute_legal_warning(self):
        html = (
            '<div class="alert alert-warning mb-0" role="alert">'
            '<strong>Yasal uyarı:</strong> Her kiracı, çağrı kaydı için gerekli rızayı almak ve '
            'yerel mevzuata uymakla yükümlüdür. TCRM otomatik olarak yasal izin vermez.'
            '</div>'
        )
        for rec in self:
            rec.legal_warning = html

    @api.depends('account_sid', 'api_key_sid', 'twiml_app_sid', 'verified_caller_id',
                 'api_key_secret_encrypted', 'auth_token_encrypted')
    def _compute_masks(self):
        for rec in self:
            rec.account_sid_masked = mask_sid(rec.account_sid)
            rec.api_key_sid_masked = mask_sid(rec.api_key_sid)
            rec.twiml_app_sid_masked = mask_sid(rec.twiml_app_sid)
            rec.verified_caller_id_masked = mask_secret(rec.verified_caller_id, keep=4)
            rec.has_api_key_secret = bool(rec.api_key_secret_encrypted)
            rec.has_auth_token = bool(rec.auth_token_encrypted)

    @api.depends(
        'account_sid', 'api_key_sid', 'api_key_secret_encrypted', 'auth_token_encrypted',
        'twiml_app_sid', 'verified_caller_id',
    )
    def _compute_is_configured(self):
        for rec in self:
            rec.is_configured = bool(
                rec.account_sid and rec.api_key_sid and rec.api_key_secret_encrypted
                and rec.auth_token_encrypted and rec.twiml_app_sid and rec.verified_caller_id
            )

    def _inverse_api_key_secret(self):
        for rec in self:
            value = rec.api_key_secret
            if not value or value == SECRET_PLACEHOLDER:
                continue
            rec.api_key_secret_encrypted = encrypt_secret(self.env, value)

    def _inverse_auth_token(self):
        for rec in self:
            value = rec.auth_token
            if not value or value == SECRET_PLACEHOLDER:
                continue
            rec.auth_token_encrypted = encrypt_secret(self.env, value)

    @api.model_create_multi
    def create(self, vals_list):
        self._check_admin()
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            self._absorb_secret_writes(vals)
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        self._check_admin()
        vals = dict(vals)
        self._absorb_secret_writes(vals)
        return super().write(vals)

    def _absorb_secret_writes(self, vals):
        if 'api_key_secret' in vals:
            secret = vals.pop('api_key_secret')
            if secret and secret != SECRET_PLACEHOLDER:
                vals['api_key_secret_encrypted'] = encrypt_secret(self.env, secret)
        if 'auth_token' in vals:
            token = vals.pop('auth_token')
            if token and token != SECRET_PLACEHOLDER:
                vals['auth_token_encrypted'] = encrypt_secret(self.env, token)

    def _check_admin(self):
        if self.env.su:
            return
        if not self.env.user.has_group('tcrm_call_center.group_santral_admin'):
            raise AccessError(_('Yalnızca Santral Yöneticisi sağlayıcı ayarlarını düzenleyebilir.'))

    def read(self, fields=None, load='_classic_read'):
        rows = super().read(fields=fields, load=load)
        is_admin = self.env.user.has_group('tcrm_call_center.group_santral_admin') or self.env.su
        for row in rows:
            # Never return ciphertext or plaintext secrets to the browser.
            if 'api_key_secret_encrypted' in row:
                row['api_key_secret_encrypted'] = bool(row['api_key_secret_encrypted'])
            if 'auth_token_encrypted' in row:
                row['auth_token_encrypted'] = bool(row['auth_token_encrypted'])
            if 'api_key_secret' in row:
                row['api_key_secret'] = SECRET_PLACEHOLDER if is_admin else False
            if 'auth_token' in row:
                row['auth_token'] = SECRET_PLACEHOLDER if is_admin else False
            if not is_admin:
                for key in ('account_sid', 'api_key_sid', 'twiml_app_sid', 'verified_caller_id',
                            'public_callback_base_url'):
                    if key in row:
                        row[key] = False
        return rows

    def export_data(self, fields_to_export):
        """Never include secrets in exports."""
        blocked = {
            'api_key_secret', 'auth_token',
            'api_key_secret_encrypted', 'auth_token_encrypted',
        }
        safe_fields = [f for f in fields_to_export if f.split('/')[0] not in blocked]
        return super().export_data(safe_fields)

    @api.model
    def get_for_company(self, company=None, require_enabled=False):
        company = company or self.env.company
        config = self.sudo().search([('company_id', '=', company.id)], limit=1)
        if not config:
            return self.browse()
        if require_enabled and (not config.enabled or not config.is_configured):
            return self.browse()
        return config

    def get_decrypted_secrets(self):
        self.ensure_one()
        self._check_admin()
        return {
            'api_key_secret': decrypt_secret(self.env, self.api_key_secret_encrypted),
            'auth_token': decrypt_secret(self.env, self.auth_token_encrypted),
        }

    def get_public_callback_base(self) -> str:
        self.ensure_one()
        base = (self.public_callback_base_url or '').strip().rstrip('/')
        if base:
            return base
        # Fall back to configured web.base.url — never trust raw Host blindly in callers.
        return (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')

    def action_test_connection(self):
        self.ensure_one()
        self._check_admin()
        if not self.is_configured:
            self.write({
                'last_connection_test': fields.Datetime.now(),
                'last_connection_status': 'missing',
                'last_error': 'Yapılandırma gerekli',
            })
            raise UserError(_('Santral yapılandırılmamış'))
        try:
            provider = get_provider(self.env, self)
            result = provider.test_connection()
        except Exception as exc:
            # Never log secrets or full provider payloads.
            msg = str(exc)[:500]
            _logger.warning('Santral connection test failed company=%s err=%s', self.company_id.id, msg)
            self.write({
                'last_connection_test': fields.Datetime.now(),
                'last_connection_status': 'error',
                'last_error': msg,
            })
            raise UserError(_('Bağlantı testi başarısız: %s') % msg) from exc
        self.write({
            'last_connection_test': fields.Datetime.now(),
            'last_connection_status': 'ok',
            'last_error': False,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bağlantıyı Test Et'),
                'message': result.get('message') or _('OK'),
                'type': 'success',
                'sticky': False,
            },
        }

    @api.constrains('enabled', 'account_sid', 'api_key_sid', 'twiml_app_sid', 'verified_caller_id')
    def _check_enabled_requires_config(self):
        for rec in self:
            if rec.enabled and not rec.is_configured:
                raise ValidationError(_('Santral etkinleştirilmeden önce yapılandırılmalıdır.'))

    def master_safe_status(self) -> dict:
        """Safe status payload for tcrm_saas_core Santral Yönetimi (no secrets)."""
        self.ensure_one()
        last_call = self.env['tcrm.call.record'].sudo().search(
            [('company_id', '=', self.company_id.id)], order='id desc', limit=1,
        )
        return {
            'company_id': self.company_id.id,
            'company_name': self.company_id.name,
            'configured': bool(self.is_configured),
            'enabled': bool(self.enabled),
            'provider': self.provider,
            'account_sid_masked': mask_sid(self.account_sid),
            'caller_id_masked': mask_secret(self.verified_caller_id, keep=4),
            'last_connection_test': fields.Datetime.to_string(self.last_connection_test) if self.last_connection_test else False,
            'last_connection_status': self.last_connection_status,
            'last_error_status': (self.last_error or '')[:200] if self.last_connection_status == 'error' else False,
            'last_call_time': fields.Datetime.to_string(last_call.create_date) if last_call else False,
        }
