# -*- coding: utf-8 -*-
"""Software-owner Santral status on tcrm.tenant (control plane)."""
from __future__ import annotations

import logging

from tcrm import api, fields, models, _
from tcrm.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class TcrmTenantSantral(models.Model):
    _inherit = 'tcrm.tenant'

    santral_configured = fields.Boolean(string='Santral Configured', compute='_compute_santral_status')
    santral_enabled = fields.Boolean(string='Santral Enabled', compute='_compute_santral_status')
    santral_provider = fields.Char(string='Santral Provider', compute='_compute_santral_status')
    santral_account_sid_masked = fields.Char(compute='_compute_santral_status')
    santral_caller_id_masked = fields.Char(compute='_compute_santral_status')
    santral_last_connection_test = fields.Datetime(compute='_compute_santral_status')
    santral_last_connection_status = fields.Char(compute='_compute_santral_status')
    santral_last_call_time = fields.Datetime(compute='_compute_santral_status')
    santral_last_error_status = fields.Char(compute='_compute_santral_status')
    santral_status_label = fields.Char(compute='_compute_santral_status')

    def _santral_env_for_tenant(self):
        """Return env bound to tenant data location (same DB company or dedicated DB)."""
        self.ensure_one()
        if self.db_name and self.db_name != self.env.cr.dbname:
            try:
                from tcrm.modules.registry import Registry
            except ImportError:  # pragma: no cover
                from odoo.modules.registry import Registry  # type: ignore
            if not self.env.user.has_group('base.group_system'):
                raise AccessError(_('Yalnızca sistem yöneticisi kiracı veritabanına erişebilir.'))
            registry = Registry(self.db_name)
            cr = registry.cursor()
            try:
                from tcrm.api import Environment
            except ImportError:  # pragma: no cover
                from odoo.api import Environment  # type: ignore
            env = Environment(cr, self.env.uid, {'lang': self.env.lang})
            # Caller must close cursor after use.
            env.tcrm_external_cr = cr
            return env
        return self.env

    def _read_santral_safe_status(self):
        self.ensure_one()
        empty = {
            'configured': False,
            'enabled': False,
            'provider': False,
            'account_sid_masked': False,
            'caller_id_masked': False,
            'last_connection_test': False,
            'last_connection_status': 'missing',
            'last_call_time': False,
            'last_error_status': False,
        }
        env = None
        external_cr = None
        try:
            env = self._santral_env_for_tenant()
            external_cr = getattr(env, 'tcrm_external_cr', None)
            if 'tcrm.call.provider.config' not in env:
                return empty
            company = env['res.company'].browse(self.company_id.id)
            if not company.exists():
                # Dedicated DB may have different company ids — use first company.
                company = env['res.company'].search([], limit=1)
            config = env['tcrm.call.provider.config'].sudo().search([
                ('company_id', '=', company.id),
            ], limit=1)
            if not config:
                return empty
            return config.master_safe_status()
        except Exception as exc:
            _logger.warning('Santral status read failed tenant=%s err=%s', self.id, str(exc)[:200])
            empty['last_error_status'] = 'status_unavailable'
            return empty
        finally:
            if external_cr is not None:
                external_cr.close()

    def _compute_santral_status(self):
        for rec in self:
            status = rec._read_santral_safe_status()
            rec.santral_configured = bool(status.get('configured'))
            rec.santral_enabled = bool(status.get('enabled'))
            rec.santral_provider = status.get('provider') or False
            rec.santral_account_sid_masked = status.get('account_sid_masked') or False
            rec.santral_caller_id_masked = status.get('caller_id_masked') or False
            rec.santral_last_connection_test = status.get('last_connection_test') or False
            rec.santral_last_connection_status = status.get('last_connection_status') or False
            rec.santral_last_call_time = status.get('last_call_time') or False
            rec.santral_last_error_status = status.get('last_error_status') or False
            if not status.get('configured'):
                rec.santral_status_label = 'Yapılandırma gerekli'
            elif not status.get('enabled'):
                rec.santral_status_label = 'Kapalı'
            else:
                rec.santral_status_label = 'Yapılandırıldı'

    def action_manage_santral_settings(self):
        """Open tenant Santral settings via existing ghost-login / company switch mechanism."""
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_('Yalnızca yazılım sahibi yöneticisi Santral ayarlarını yönetebilir.'))
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        if self.db_name:
            url = '%s/tcrm?db=%s#action=tcrm_call_center.action_tcrm_call_provider_config' % (
                base_url, self.db_name,
            )
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }
        # Same-DB multi-company: open config for tenant company.
        config = self.env['tcrm.call.provider.config'].sudo().search([
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not config:
            config = self.env['tcrm.call.provider.config'].sudo().create({
                'company_id': self.company_id.id,
                'provider': 'twilio',
                'enabled': False,
            })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Santral Ayarlarını Yönet'),
            'res_model': 'tcrm.call.provider.config',
            'res_id': config.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'allowed_company_ids': [self.company_id.id]},
        }
