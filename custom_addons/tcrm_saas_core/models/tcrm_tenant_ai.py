# Part of TCRM SaaS Core. See LICENSE for details.
"""Safe TCRM AI entitlement status mirrored on the master/control database."""
from __future__ import annotations

import logging

from tcrm import api, fields, models, _
from tcrm.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

AI_MODULE_NAME = 'tcrm_ai'

AI_STATES = [
    ('unavailable', 'Kullanılamaz'),
    ('granted', 'Erişim Verildi'),
    ('config_required', 'Yapılandırma Gerekli'),
    ('active', 'Aktif'),
    ('suspended', 'Askıya Alındı'),
    ('quota_exceeded', 'Kota Aşıldı'),
    ('connection_error', 'Bağlantı Hatası'),
]


class TcrmTenantAiStatus(models.Model):
    _name = 'tcrm.tenant.ai.status'
    _description = 'Tenant TCRM AI Safe Status'
    _order = 'id desc'

    tenant_id = fields.Many2one('tcrm.tenant', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='tenant_id.company_id', store=True, readonly=True)
    domain = fields.Char(related='tenant_id.primary_domain', store=True, readonly=True)
    entitlement_state = fields.Selection(AI_STATES, string='Entitlement', default='unavailable', required=True)
    module_installed = fields.Boolean(default=False)
    provider = fields.Char()
    model = fields.Char()
    configured = fields.Boolean(default=False)
    enabled = fields.Boolean(default=False)
    requests_this_month = fields.Integer(default=0)
    tokens_this_month = fields.Integer(default=0)
    last_connection_status = fields.Char()
    last_request_date = fields.Datetime()
    last_safe_error = fields.Char()
    last_sync = fields.Datetime()

    _sql_constraints = [
        ('tcrm_tenant_ai_status_uniq', 'unique(tenant_id)', 'AI status already exists for this tenant.'),
    ]

    def _require_master_admin(self):
        if not (
            self.env.user.has_group('base.group_system')
            or self.env.user.has_group('tcrm_saas_core.group_tcrm_tenant_admin')
        ):
            raise AccessError(_('Master administrator privileges required.'))

    @api.model
    def get_or_create(self, tenant):
        rec = self.search([('tenant_id', '=', tenant.id)], limit=1)
        if not rec:
            rec = self.create({'tenant_id': tenant.id, 'entitlement_state': 'unavailable'})
        return rec

    def _open_tenant_env(self, tenant):
        db_name = (tenant.db_name or '').strip()
        if not db_name:
            raise UserError(_('Tenant has no dedicated database.'))
        from tcrm.modules.registry import Registry
        from tcrm import api as tcrm_api, SUPERUSER_ID
        registry = Registry(db_name)
        return registry, tcrm_api, SUPERUSER_ID

    def action_grant_access(self):
        """Grant TCRM AI entitlement, install module in tenant DB, seed empty config."""
        self._require_master_admin()
        for status in self:
            tenant = status.tenant_id
            Module = self.env['ir.module.module'].sudo()
            module = Module.search([('name', '=', AI_MODULE_NAME)], limit=1)
            if not module:
                raise UserError(_('tcrm_ai module is not present on this server.'))
            tenant.action_grant_module(module, state='allowed', note='TCRM AI')

            if not tenant.db_name:
                status.write({
                    'entitlement_state': 'granted',
                    'module_installed': False,
                    'configured': False,
                    'enabled': False,
                    'last_sync': fields.Datetime.now(),
                })
                continue

            registry, tcrm_api, SUPERUSER_ID = self._open_tenant_env(tenant)
            with registry.cursor() as cr:
                tenv = tcrm_api.Environment(cr, SUPERUSER_ID, {})
                tmod = tenv['ir.module.module'].search([('name', '=', AI_MODULE_NAME)], limit=1)
                installed = False
                if tmod:
                    if tmod.state != 'installed':
                        try:
                            tmod.button_immediate_install()
                        except Exception:
                            _logger.exception('Failed installing tcrm_ai on tenant db=%s', tenant.db_name)
                            # Fallback: mark to install
                            try:
                                tmod.button_install()
                            except Exception:
                                pass
                    installed = tmod.state in ('installed', 'to upgrade', 'to install')
                # Seed entitlement + empty disabled config — never copy owner key
                tenv['ir.config_parameter'].sudo().set_param('tcrm_ai.entitlement_state', 'config_required')
                tenv['ir.config_parameter'].sudo().set_param('tcrm_ai.suspended', '0')
                if 'tcrm.ai.config' in tenv:
                    config = tenv['tcrm.ai.config'].sudo().get_config()
                    config.sudo().write({
                        'ai_enabled': False,
                        'api_key_encrypted': False,
                        'provider': 'groq',
                        'model': 'openai/gpt-oss-20b',
                        'base_url': 'https://api.groq.com/openai/v1',
                    })
                    # Ensure AI admin group exists for tenant admin
                    group = tenv.ref('tcrm_ai.group_tcrm_ai_admin', raise_if_not_found=False)
                    admin = tenv.ref('base.user_admin', raise_if_not_found=False)
                    if group and admin and group not in admin.groups_id:
                        admin.sudo().write({'groups_id': [(4, group.id)]})
                    user_group = tenv.ref('tcrm_ai.group_tcrm_ai_user', raise_if_not_found=False)
                    if user_group and admin and user_group not in admin.groups_id:
                        admin.sudo().write({'groups_id': [(4, user_group.id)]})
                cr.commit()
                status.write({
                    'entitlement_state': 'config_required',
                    'module_installed': bool(installed or ('tcrm.ai.config' in tenv)),
                    'configured': False,
                    'enabled': False,
                    'provider': 'groq',
                    'model': 'openai/gpt-oss-20b',
                    'last_safe_error': False,
                    'last_sync': fields.Datetime.now(),
                })
        return True

    def action_revoke_access(self):
        """Revoke entitlement; block endpoints; keep conversations and keys."""
        self._require_master_admin()
        for status in self:
            tenant = status.tenant_id
            module = self.env['ir.module.module'].sudo().search([('name', '=', AI_MODULE_NAME)], limit=1)
            if module:
                tenant.action_revoke_module(module)
            if tenant.db_name:
                try:
                    registry, tcrm_api, SUPERUSER_ID = self._open_tenant_env(tenant)
                    with registry.cursor() as cr:
                        tenv = tcrm_api.Environment(cr, SUPERUSER_ID, {})
                        tenv['ir.config_parameter'].sudo().set_param('tcrm_ai.entitlement_state', 'unavailable')
                        tenv['ir.config_parameter'].sudo().set_param('tcrm_ai.suspended', '0')
                        if 'tcrm.ai.config' in tenv:
                            config = tenv['tcrm.ai.config'].sudo().search([], limit=1)
                            if config:
                                config.sudo().write({'ai_enabled': False})
                        cr.commit()
                except Exception:
                    _logger.exception('Failed revoking AI on tenant=%s', tenant.id)
            status.write({
                'entitlement_state': 'unavailable',
                'enabled': False,
                'last_sync': fields.Datetime.now(),
            })
        return True

    def action_suspend(self):
        self._require_master_admin()
        for status in self:
            tenant = status.tenant_id
            if tenant.db_name:
                registry, tcrm_api, SUPERUSER_ID = self._open_tenant_env(tenant)
                with registry.cursor() as cr:
                    tenv = tcrm_api.Environment(cr, SUPERUSER_ID, {})
                    tenv['ir.config_parameter'].sudo().set_param('tcrm_ai.entitlement_state', 'suspended')
                    tenv['ir.config_parameter'].sudo().set_param('tcrm_ai.suspended', '1')
                    if 'tcrm.ai.config' in tenv:
                        config = tenv['tcrm.ai.config'].sudo().search([], limit=1)
                        if config:
                            config.sudo().write({'ai_enabled': False})
                    cr.commit()
            status.write({'entitlement_state': 'suspended', 'enabled': False, 'last_sync': fields.Datetime.now()})
        return True

    def action_refresh_safe_status(self):
        """Pull safe (non-secret) status from the tenant database."""
        self._require_master_admin()
        for status in self:
            tenant = status.tenant_id
            if not tenant.db_name:
                continue
            try:
                registry, tcrm_api, SUPERUSER_ID = self._open_tenant_env(tenant)
                with registry.cursor() as cr:
                    tenv = tcrm_api.Environment(cr, SUPERUSER_ID, {})
                    vals = {
                        'last_sync': fields.Datetime.now(),
                        'module_installed': 'tcrm.ai.config' in tenv,
                    }
                    if 'tcrm.ai.config' in tenv:
                        pub = tenv['tcrm.ai.config'].sudo().get_public_status()
                        vals.update({
                            'entitlement_state': pub.get('entitlement_status') or status.entitlement_state,
                            'provider': pub.get('provider') or '',
                            'model': pub.get('model') or '',
                            'configured': bool(pub.get('configured')),
                            'enabled': bool(pub.get('ai_enabled')),
                            'last_connection_status': pub.get('last_connection_status') or '',
                            'last_safe_error': pub.get('last_safe_error') or '',
                            'requests_this_month': int((pub.get('usage') or {}).get('monthly_requests') or 0),
                            'tokens_this_month': int((pub.get('usage') or {}).get('monthly_tokens') or 0),
                        })
                    status.write(vals)
            except Exception:
                _logger.exception('AI status refresh failed tenant=%s', tenant.id)
                status.write({'last_safe_error': _('Durum senkronu başarısız'), 'last_sync': fields.Datetime.now()})
        return True

    def action_manage_configuration(self):
        """
        Securely open tenant-local AI configuration via dedicated DB context.
        Never copies secrets back to master.
        """
        self._require_master_admin()
        self.ensure_one()
        tenant = self.tenant_id
        if not tenant.db_name:
            raise UserError(_('Tenant has no dedicated database.'))
        # Refresh and return notification — actual secret writes happen inside tenant DB only
        self.action_refresh_safe_status()
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        login_url = ('https://%s/web' % tenant.primary_domain) if tenant.primary_domain else base
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('TCRM AI'),
                'message': _(
                    'Yapılandırma tenant veritabanında tutulur. Tenant yöneticisi ile giriş yapın: %s — Ayarlar > TCRM AI'
                ) % login_url,
                'type': 'info',
                'sticky': True,
            },
        }

    def to_safe_dict(self):
        self.ensure_one()
        return {
            'id': self.id,
            'tenant_id': self.tenant_id.id,
            'tenant': self.tenant_id.name,
            'domain': self.domain or '',
            'entitlement': self.entitlement_state,
            'module_installed': self.module_installed,
            'provider': self.provider or '',
            'model': self.model or '',
            'configured': self.configured,
            'enabled': self.enabled,
            'requests_this_month': self.requests_this_month,
            'tokens_this_month': self.tokens_this_month,
            'last_connection_status': self.last_connection_status or '',
            'last_request_date': fields.Datetime.to_string(self.last_request_date) if self.last_request_date else '',
            'last_safe_error': self.last_safe_error or '',
        }


class TcrmTenantAi(models.Model):
    _inherit = 'tcrm.tenant'

    ai_status_id = fields.Many2one('tcrm.tenant.ai.status', compute='_compute_ai_status', store=False)

    def _compute_ai_status(self):
        Status = self.env['tcrm.tenant.ai.status']
        for tenant in self:
            tenant.ai_status_id = Status.get_or_create(tenant)

    def action_grant_tcrm_ai(self):
        for tenant in self:
            status = self.env['tcrm.tenant.ai.status'].get_or_create(tenant)
            status.action_grant_access()
        return True

    def action_revoke_tcrm_ai(self):
        for tenant in self:
            status = self.env['tcrm.tenant.ai.status'].get_or_create(tenant)
            status.action_revoke_access()
        return True
