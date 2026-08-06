# -*- coding: utf-8 -*-
"""Deny deep-link / action load of the Apps Gallery on tenant databases."""
from tcrm import models, _
from tcrm.exceptions import AccessError

BLOCKED_APPS_ACTION_XMLIDS = (
    'base.open_module_tree',
)


def _is_master_database(env):
    """Control-plane DB only (never trust model presence — tenants may have saas_core)."""
    try:
        from tcrm.tools import config
        control_db = config.get('tcrm_control_db') or 'tcrm_master'
    except Exception:
        control_db = 'tcrm_master'
    return env.cr.dbname == control_db


class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    def _tcrm_block_apps_store_action(self):
        if self.env.su or _is_master_database(self.env):
            return
        for xmlid in BLOCKED_APPS_ACTION_XMLIDS:
            action = self.env.ref(xmlid, raise_if_not_found=False)
            if action and (self & action):
                raise AccessError(_(
                    'Apps Store is disabled for tenants. '
                    'Modules are managed exclusively by TCRM Master.'
                ))

    def read(self, fields=None, load='_classic_read'):
        self._tcrm_block_apps_store_action()
        return super().read(fields=fields, load=load)
