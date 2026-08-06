# -*- coding: utf-8 -*-
"""Block tenant Apps Store / module install UI (managed by TCRM Master)."""
import logging

from tcrm import api, models, _
from tcrm.exceptions import AccessError

_logger = logging.getLogger(__name__)

APPS_GALLERY_MENU_XMLIDS = (
    'base.menu_management',
    'base.menu_apps',
    'base.menu_module_tree',
    'base_import_module.menu_view_base_module_import',
)


def _is_master_database(env):
    """Control-plane DB only (never trust model presence — tenants may have saas_core)."""
    try:
        from tcrm.tools import config
        control_db = config.get('tcrm_control_db') or 'tcrm_master'
    except Exception:
        control_db = 'tcrm_master'
    return env.cr.dbname == control_db


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def _tcrm_ensure_tenant_module_ops_allowed(self):
        """Tenants cannot install/upgrade/uninstall modules from the UI.

        Superuser / shell / provisioning (sudo) remain allowed so the control
        plane can still provision and maintain tenant databases.
        """
        if self.env.su or _is_master_database(self.env):
            return
        raise AccessError(_(
            'Apps Store is disabled for tenants. '
            'Modules are managed exclusively by TCRM Master.'
        ))

    def button_immediate_install(self):
        self._tcrm_ensure_tenant_module_ops_allowed()
        return super().button_immediate_install()

    def button_install(self):
        self._tcrm_ensure_tenant_module_ops_allowed()
        return super().button_install()

    def button_immediate_upgrade(self):
        self._tcrm_ensure_tenant_module_ops_allowed()
        return super().button_immediate_upgrade()

    def button_upgrade(self):
        self._tcrm_ensure_tenant_module_ops_allowed()
        return super().button_upgrade()

    def button_immediate_uninstall(self):
        self._tcrm_ensure_tenant_module_ops_allowed()
        return super().button_immediate_uninstall()

    def button_uninstall(self):
        self._tcrm_ensure_tenant_module_ops_allowed()
        return super().button_uninstall()

    @api.model
    def _tcrm_hide_apps_gallery_for_tenants(self):
        """Primary SaaS rule: disable Apps Store UI on every tenant DB."""
        env = self.env
        if _is_master_database(env):
            _logger.info('TCRM: Apps Gallery kept active on master DB')
            return True

        hidden = []
        for xmlid in APPS_GALLERY_MENU_XMLIDS:
            menu = env.ref(xmlid, raise_if_not_found=False)
            if menu and menu.active:
                menu.sudo().write({'active': False})
                hidden.append(xmlid)

        root = env.ref('base.menu_management', raise_if_not_found=False)
        group_system = env.ref('base.group_system', raise_if_not_found=False)
        if root and group_system:
            vals = {}
            if 'group_ids' in root._fields:
                vals['group_ids'] = [(6, 0, [group_system.id])]
            elif 'groups_id' in root._fields:
                vals['groups_id'] = [(6, 0, [group_system.id])]
            if vals:
                root.sudo().write(vals)

        if hidden:
            env.registry.clear_cache()
            _logger.info('TCRM: Apps Gallery hidden for tenant DB: %s', ', '.join(hidden))
        else:
            _logger.info('TCRM: Apps Gallery already hidden on tenant DB')
        return True

    @api.model
    def _tcrm_disable_tcrm_com_oauth_login(self):
        """Hide 'Sign in with Tcrm.com' / 'Tcrm.com ile oturum açın' on login pages."""
        env = self.env
        if 'auth.oauth.provider' not in env:
            return True
        Provider = env['auth.oauth.provider'].sudo()
        providers = Provider.search([
            '|', '|',
            ('name', 'ilike', 'Tcrm.com'),
            ('auth_endpoint', 'ilike', 'accounts.tcrm.com'),
            ('css_class', 'ilike', 'o_tcrm_provider'),
        ])
        seeded = env.ref('auth_oauth.provider_openerp', raise_if_not_found=False)
        if seeded:
            providers |= seeded
        enabled = providers.filtered('enabled')
        if enabled:
            enabled.write({'enabled': False})
            _logger.info('TCRM: disabled %s Tcrm.com OAuth login provider(s)', len(enabled))
        return True
