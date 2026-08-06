# Part of TCRM SaaS Core. See LICENSE for details.
"""Mirrored tenant application inventory (installed vs entitlement)."""
from __future__ import annotations

import logging
from datetime import timedelta

from tcrm import api, fields, models, _
from tcrm.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

INVENTORY_STATES = [
    ('granted_installed', 'Granted and installed'),
    ('granted_not_installed', 'Granted but not installed'),
    ('installed_not_granted', 'Installed but not granted'),
    ('not_installed', 'Not installed'),
    ('to_install', 'Pending installation'),
    ('to_upgrade', 'Upgrade required'),
    ('install_failed', 'Installation failed'),
    ('unreachable', 'Tenant unreachable'),
]

STALE_HOURS = 24

# Never uninstall these from a tenant — platform / CRM hard deps.
NEVER_UNINSTALL = frozenset({
    'base', 'web', 'mail', 'mail_bot', 'bus', 'web_tour', 'base_setup', 'base_import',
    'auth_signup', 'auth_totp', 'auth_password_policy', 'auth_passkey',
    'http_routing', 'rpc', 'utm', 'iap', 'html_editor', 'web_editor', 'portal',
    'social_media', 'contacts', 'calendar', 'phone_validation', 'sms', 'resource',
    'digest', 'partner_autocomplete', 'tcrm_web_enhance', 'tcrm_saas_routing',
})


class TcrmTenantAppInventory(models.Model):
    _name = 'tcrm.tenant.app.inventory'
    _description = 'Tenant Application Inventory'
    _order = 'name, technical_name'

    tenant_id = fields.Many2one('tcrm.tenant', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='tenant_id.company_id', store=True, readonly=True)
    technical_name = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    version = fields.Char()
    category = fields.Char(string='Application Category')
    is_application = fields.Boolean(default=True, help='User-facing application module')
    is_technical = fields.Boolean(default=False, help='Hidden technical dependency by default')
    installed_state = fields.Char(string='Installed State')
    entitlement_state = fields.Selection(
        [('allowed', 'Allowed'), ('blocked', 'Blocked'), ('trial', 'Trial'), ('none', 'None')],
        default='none',
    )
    access_state = fields.Selection(INVENTORY_STATES, string='Access State', default='not_installed', index=True)
    last_sync = fields.Datetime(string='Last Synchronized')
    last_sync_result = fields.Selection(
        [('ok', 'OK'), ('error', 'Error'), ('stale', 'Stale'), ('unreachable', 'Unreachable')],
        default='ok',
    )
    last_safe_error = fields.Char(string='Safe Error')
    source = fields.Selection(
        [('tenant_db', 'Tenant Database'), ('master_catalog', 'Master Catalog'), ('manual', 'Manual')],
        default='tenant_db',
    )
    stale = fields.Boolean(compute='_compute_stale', store=True, index=True)

    _rec_name = 'name'

    _sql_constraints = [
        ('tcrm_tenant_app_inventory_uniq', 'unique(tenant_id, technical_name)',
         'Inventory row already exists for this tenant module.'),
    ]

    @api.depends('last_sync', 'last_sync_result')
    def _compute_stale(self):
        threshold = fields.Datetime.now() - timedelta(hours=STALE_HOURS)
        for rec in self:
            rec.stale = (
                rec.last_sync_result in ('stale', 'unreachable', 'error')
                or not rec.last_sync
                or rec.last_sync < threshold
            )

    def _require_master_admin(self):
        if not (
            self.env.user.has_group('base.group_system')
            or self.env.user.has_group('tcrm_saas_core.group_tcrm_tenant_admin')
        ):
            raise AccessError(_('Master administrator privileges required.'))

    def _open_tenant_env(self, tenant):
        db_name = (tenant.db_name or '').strip()
        if not db_name:
            raise UserError(_('Tenant has no dedicated database.'))
        # Never accept browser-submitted arbitrary DB names — only tenant.db_name.
        from tcrm.modules.registry import Registry
        from tcrm import api as tcrm_api, SUPERUSER_ID
        registry = Registry(db_name)
        return registry, tcrm_api, SUPERUSER_ID

    def _compute_access_state(self, entitlement_state, installed_state, is_application=True):
        inst = (installed_state or '').strip()
        ent = entitlement_state or 'none'
        if inst == 'unreachable':
            return 'unreachable'
        granted = ent in ('allowed', 'trial')
        if inst == 'installed':
            return 'granted_installed' if granted else 'installed_not_granted'
        if inst in ('to install', 'to_install'):
            return 'to_install'
        if inst in ('to upgrade', 'to_upgrade'):
            return 'to_upgrade'
        if inst in ('uninstallable',) and granted:
            return 'granted_not_installed'
        if granted:
            return 'granted_not_installed'
        return 'not_installed'

    @api.model
    def action_sync_tenant(self, tenant):
        """Pull actual ir.module.module state from the tenant DB and merge entitlements."""
        self._require_master_admin()
        tenant.ensure_one()
        Inventory = self.sudo()
        Ent = self.env['tcrm.tenant.module.entitlement'].sudo()
        now = fields.Datetime.now()
        entitlements = {
            e.module_id.name: e.state
            for e in Ent.search([('tenant_id', '=', tenant.id)])
            if e.module_id
        }

        if not tenant.db_name:
            # Mark known entitlement rows as unreachable / not installed.
            for tech, ent_state in entitlements.items():
                self._upsert_row(tenant, {
                    'technical_name': tech,
                    'name': tech,
                    'installed_state': 'uninstalled',
                    'entitlement_state': ent_state,
                    'access_state': self._compute_access_state(ent_state, 'uninstalled'),
                    'last_sync': now,
                    'last_sync_result': 'unreachable',
                    'last_safe_error': 'Tenant has no dedicated database',
                    'source': 'master_catalog',
                    'is_application': True,
                    'is_technical': False,
                })
            return {'ok': False, 'error': 'no_db', 'count': 0}

        try:
            registry, tcrm_api, SUPERUSER_ID = self._open_tenant_env(tenant)
        except Exception as exc:
            _logger.warning('Tenant inventory sync unreachable tenant=%s: %s', tenant.id, type(exc).__name__)
            for tech, ent_state in entitlements.items():
                self._upsert_row(tenant, {
                    'technical_name': tech,
                    'name': tech,
                    'installed_state': 'unreachable',
                    'entitlement_state': ent_state,
                    'access_state': 'unreachable',
                    'last_sync': now,
                    'last_sync_result': 'unreachable',
                    'last_safe_error': type(exc).__name__,
                    'source': 'tenant_db',
                    'is_application': True,
                    'is_technical': False,
                })
            return {'ok': False, 'error': 'unreachable', 'count': 0}

        rows = []
        try:
            with registry.cursor() as cr:
                tenv = tcrm_api.Environment(cr, SUPERUSER_ID, {})
                Module = tenv['ir.module.module']
                # Prefer user-facing apps; also keep product modules even if application=False.
                modules = Module.search([
                    '|',
                    ('application', '=', True),
                    ('name', 'in', [
                        'tcrm_propertio', 'tcrm_call_center', 'tcrm_web_enhance',
                        'tcrm_ai', 'tcrm_saas_core', 'tcrm_offer', 'contacts', 'calendar',
                        'project', 'hr', 'account', 'sale_management', 'crm',
                    ]),
                ])
                seen = set()
                for mod in modules:
                    tech = mod.name
                    seen.add(tech)
                    ent_state = entitlements.get(tech, 'none')
                    is_app = bool(mod.application)
                    rows.append({
                        'technical_name': tech,
                        'name': mod.shortdesc or mod.name,
                        'version': mod.latest_version or mod.installed_version or '',
                        'category': mod.category_id.display_name if mod.category_id else '',
                        'is_application': is_app,
                        'is_technical': not is_app,
                        'installed_state': mod.state,
                        'entitlement_state': ent_state,
                        'access_state': self._compute_access_state(ent_state, mod.state, is_app),
                        'last_sync': now,
                        'last_sync_result': 'ok',
                        'last_safe_error': False,
                        'source': 'tenant_db',
                    })
                # Entitlement-only modules missing from tenant module list
                for tech, ent_state in entitlements.items():
                    if tech in seen:
                        continue
                    rows.append({
                        'technical_name': tech,
                        'name': tech,
                        'version': '',
                        'category': '',
                        'is_application': True,
                        'is_technical': False,
                        'installed_state': 'uninstalled',
                        'entitlement_state': ent_state,
                        'access_state': self._compute_access_state(ent_state, 'uninstalled'),
                        'last_sync': now,
                        'last_sync_result': 'ok',
                        'last_safe_error': False,
                        'source': 'master_catalog',
                    })
        except Exception as exc:
            _logger.exception('Tenant inventory sync failed tenant=%s', tenant.id)
            return {'ok': False, 'error': type(exc).__name__, 'count': 0}

        for vals in rows:
            self._upsert_row(tenant, vals)

        # Drop stale inventory rows no longer present
        keep = {r['technical_name'] for r in rows}
        Inventory.search([
            ('tenant_id', '=', tenant.id),
            ('technical_name', 'not in', list(keep) or [False]),
        ]).unlink()
        return {'ok': True, 'count': len(rows), 'stale': False}

    def _upsert_row(self, tenant, vals):
        Inventory = self.sudo()
        existing = Inventory.search([
            ('tenant_id', '=', tenant.id),
            ('technical_name', '=', vals['technical_name']),
        ], limit=1)
        payload = dict(vals, tenant_id=tenant.id)
        if existing:
            existing.write(payload)
            return existing
        return Inventory.create(payload)

    @api.model
    def cron_sync_all_tenants(self):
        tenants = self.env['tcrm.tenant'].sudo().search([('db_name', '!=', False)])
        for tenant in tenants:
            try:
                self.action_sync_tenant(tenant)
            except Exception:
                _logger.exception('cron inventory sync failed tenant=%s', tenant.id)
        return True

    def action_grant_access(self):
        self._require_master_admin()
        Module = self.env['ir.module.module'].sudo()
        for rec in self:
            module = Module.search([('name', '=', rec.technical_name)], limit=1)
            if not module:
                raise UserError(_('Module %s is not present on the master server.') % rec.technical_name)
            rec.tenant_id.action_grant_module(module, state='allowed', note='Inventory grant')
            rec.entitlement_state = 'allowed'
            rec.access_state = self._compute_access_state('allowed', rec.installed_state)
        return True

    def action_revoke_access(self):
        """Block entitlement only (module stays installed until Uninstall)."""
        self._require_master_admin()
        Module = self.env['ir.module.module'].sudo()
        for rec in self:
            module = Module.search([('name', '=', rec.technical_name)], limit=1)
            if module:
                rec.tenant_id.action_revoke_module(module)
            rec.entitlement_state = 'blocked'
            rec.access_state = self._compute_access_state('blocked', rec.installed_state)
        return True

    def action_revoke_and_uninstall(self):
        """Block entitlement and uninstall the app from the tenant DB."""
        self.action_revoke_access()
        return self.action_queue_uninstall()

    def _can_uninstall(self, technical_name):
        name = (technical_name or '').strip()
        if not name or name in NEVER_UNINSTALL:
            return False
        if name.startswith('base') or name.startswith('web_') and name in NEVER_UNINSTALL:
            return False
        return True

    def action_queue_uninstall(self):
        """Uninstall module on tenant DB (master SUPERUSER). Protected modules skipped."""
        self._require_master_admin()
        for rec in self:
            if not rec.tenant_id.db_name:
                raise UserError(_('Tenant has no dedicated database.'))
            if not self._can_uninstall(rec.technical_name):
                raise UserError(_(
                    'Module %s is protected and cannot be uninstalled from App Inventory.'
                ) % rec.technical_name)
            registry, tcrm_api, SUPERUSER_ID = self._open_tenant_env(rec.tenant_id)
            try:
                with registry.cursor() as cr:
                    tenv = tcrm_api.Environment(cr, SUPERUSER_ID, {})
                    mod = tenv['ir.module.module'].search(
                        [('name', '=', rec.technical_name)], limit=1
                    )
                    if not mod:
                        raise UserError(_('Module not found in tenant database.'))
                    if mod.state == 'installed':
                        # SUPERUSER bypasses tenant Apps-Store lock in tcrm_web_enhance.
                        mod.button_immediate_uninstall()
                rec.last_safe_error = False
            except Exception as e:
                rec.last_safe_error = str(e)[:500]
                rec.last_sync_result = 'error'
                _logger.exception(
                    'Uninstall failed tenant=%s module=%s',
                    rec.tenant_id.db_name, rec.technical_name,
                )
                raise UserError(_(
                    'Uninstall failed for %s: %s'
                ) % (rec.technical_name, str(e)[:300])) from e
            rec.action_sync_tenant(rec.tenant_id)
        return True

    def action_queue_install(self):
        self._require_master_admin()
        for rec in self:
            if not rec.tenant_id.db_name:
                raise UserError(_('Tenant has no dedicated database.'))
            if rec.entitlement_state not in ('allowed', 'trial'):
                raise UserError(_('Grant access before queuing installation.'))
            registry, tcrm_api, SUPERUSER_ID = self._open_tenant_env(rec.tenant_id)
            with registry.cursor() as cr:
                tenv = tcrm_api.Environment(cr, SUPERUSER_ID, {})
                mod = tenv['ir.module.module'].search([('name', '=', rec.technical_name)], limit=1)
                if not mod:
                    raise UserError(_('Module not found in tenant database.'))
                if mod.state != 'installed':
                    mod.button_immediate_install()
            rec.action_sync_tenant(rec.tenant_id)
        return True

    def action_queue_upgrade(self):
        self._require_master_admin()
        for rec in self:
            registry, tcrm_api, SUPERUSER_ID = self._open_tenant_env(rec.tenant_id)
            with registry.cursor() as cr:
                tenv = tcrm_api.Environment(cr, SUPERUSER_ID, {})
                mod = tenv['ir.module.module'].search([('name', '=', rec.technical_name)], limit=1)
                if mod and mod.state == 'installed':
                    mod.button_immediate_upgrade()
            rec.action_sync_tenant(rec.tenant_id)
        return True

    def action_view_last_sync_error(self):
        self.ensure_one()
        raise UserError(self.last_safe_error or _('No sync error recorded.'))

    def action_view_dependencies(self):
        self.ensure_one()
        raise UserError(_(
            'Dependencies for %s must be reviewed on the tenant Apps screen '
            'before uninstall or upgrade.'
        ) % self.name)


class TcrmTenantInventoryMixin(models.Model):
    _inherit = 'tcrm.tenant'

    app_inventory_ids = fields.One2many('tcrm.tenant.app.inventory', 'tenant_id', string='Application Inventory')
    app_inventory_stale = fields.Boolean(compute='_compute_app_inventory_stale')

    def _compute_app_inventory_stale(self):
        for tenant in self:
            inv = tenant.app_inventory_ids
            tenant.app_inventory_stale = bool(not inv or any(inv.mapped('stale')))

    def action_sync_applications(self):
        Inventory = self.env['tcrm.tenant.app.inventory']
        for tenant in self:
            Inventory.action_sync_tenant(tenant)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Application Inventory'),
                'message': _('Tenant applications synchronized.'),
                'type': 'success',
                'sticky': False,
            },
        }
