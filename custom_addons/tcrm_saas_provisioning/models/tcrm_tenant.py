# -*- coding: utf-8 -*-
import logging
import re

from tcrm import models, fields, api, _
from tcrm.exceptions import UserError

from . import provisioning_common as pc

_logger = logging.getLogger(__name__)

_PLATFORM_DOMAIN_SUFFIX = '.tcrm.online'
_ADMIN_LOGIN_RE = re.compile(r'^[a-zA-Z0-9._@+-]{3,64}$')


class TcrmTenant(models.Model):
    _inherit = 'tcrm.tenant'

    provision_state = fields.Selection([
        ('unprovisioned', 'Not provisioned'),
        ('queued', 'Queued'),
        ('provisioning', 'Provisioning'),
        ('provisioned', 'Provisioned'),
        ('failed', 'Failed'),
    ], string='Provisioning', default='unprovisioned', copy=False, tracking=True)
    provisioning_job_ids = fields.One2many(
        'tcrm.provisioning.job', 'tenant_id', string='Provisioning Jobs')
    provisioning_job_count = fields.Integer(compute='_compute_provisioning_job_count')

    def _compute_provisioning_job_count(self):
        for t in self:
            t.provisioning_job_count = len(t.provisioning_job_ids)

    def _create_tenant_db(self, db_name):
        """Override the base (blocked) synchronous DB creation.

        With ``list_db=False`` the web ``exp_create_database`` path is (correctly)
        disabled. Real provisioning is performed asynchronously by the privileged
        worker via a signed job, so here we only record intent and never create a
        database inside the request."""
        self.ensure_one()
        _logger.info(
            'Tenant %s: skipping synchronous DB creation for %r; use the '
            'provisioning worker (action_request_provisioning).', self.id, db_name)
        return False

    @api.model
    def _normalize_provision_domain(self, domain):
        """Normalize hostname; bare labels become <label>.tcrm.online."""
        Domain = self.env['tcrm.tenant.domain']
        d = Domain._normalize_domain(domain)
        if not d:
            raise UserError(_('Domain is required.'))
        if '.' not in d:
            d = '%s%s' % (d, _PLATFORM_DOMAIN_SUFFIX)
        return d

    @api.model
    def _ssl_status_for_domain(self, domain):
        """Initial SSL status at create time.

        Platform subdomains start as ``pending`` until ``ensure_tenant_ssl.sh``
        confirms coverage (preferred: platform wildcard ``*.tcrm.online``;
        fallback: per-host HTTP-01 expand). Custom domains stay pending.
        """
        return 'pending'

    @api.model
    def action_create_and_provision(self, vals):
        """One-shot control-plane create: tenant + primary domain + queued job.

        Expected keys:
          name, domain, db_name, admin_login, admin_password
          optional: client_name, sector_id, support_email, support_phone
        """
        name = (vals.get('name') or '').strip()
        db_name = (vals.get('db_name') or '').strip().lower()
        domain = self._normalize_provision_domain(vals.get('domain'))
        admin_login = (vals.get('admin_login') or 'admin').strip()
        admin_password = vals.get('admin_password') or ''

        if not name:
            raise UserError(_('Tenant name is required.'))
        try:
            pc.validate_db_name(db_name)
        except ValueError as exc:
            raise UserError(str(exc)) from exc
        if not _ADMIN_LOGIN_RE.match(admin_login):
            raise UserError(_(
                'Admin username must be 3-64 chars (letters, digits, . _ @ + -).'))
        if len(admin_password) < 8:
            raise UserError(_('Admin password must be at least 8 characters.'))

        Domain = self.env['tcrm.tenant.domain'].sudo()
        if Domain.search_count([('domain', '=', domain)]):
            raise UserError(_('Domain %s is already in use.') % domain)

        tenant_vals = {
            'name': name,
            'client_name': (vals.get('client_name') or name).strip() or name,
            'support_email': vals.get('support_email') or '',
            'support_phone': vals.get('support_phone') or '',
            'state': 'draft',
            'db_name': db_name,
            'provision_state': 'unprovisioned',
        }
        if vals.get('sector_id'):
            tenant_vals['sector_id'] = int(vals['sector_id'])

        tenant = self.sudo().create(tenant_vals)
        Domain.create({
            'tenant_id': tenant.id,
            'domain': domain,
            'is_primary': True,
            'active': True,
            'verified': False,
            'ssl_status': self._ssl_status_for_domain(domain),
        })
        job = self.env['tcrm.provisioning.job'].enqueue_for_tenant(
            tenant, db_name,
            admin_login=admin_login,
            admin_password=admin_password,
        )
        tenant.write({'provision_state': 'queued'})
        # Seed Access Management entitlements immediately (package + provision set).
        try:
            module_names = [n.strip() for n in (job.module_set or '').split(',') if n.strip()]
            tenant._ensure_default_subscription('growth')
            tenant._sync_entitlements_from_module_names(module_names, source='provision')
        except Exception:  # noqa: BLE001
            _logger.exception(
                'Failed to seed module entitlements for new tenant %s', tenant.id)
        _logger.info(
            'Created tenant %s (%s) with domain %s and queued job %s',
            tenant.id, db_name, domain, job.id)
        return {
            'tenant_id': tenant.id,
            'tenant_name': tenant.name,
            'domain': domain,
            'db_name': db_name,
            'job_id': job.id,
            'provision_state': tenant.provision_state,
            'ssl_status': self._ssl_status_for_domain(domain),
            'admin_login': admin_login,
        }

    def action_request_provisioning(self):
        """Control-plane action: create a *signed provisioning job* only.

        Prefer ``action_create_and_provision`` for new tenants (one screen).
        This remains for re-queue / existing draft tenants that already have
        db_name + domain filled in."""
        self.ensure_one()
        db_name = (self.db_name or '').strip()
        if not pc.is_valid_db_name(db_name):
            raise UserError(_(
                'Set a valid tenant database name first (3-63 chars, lowercase '
                'letter start, only lowercase letters/digits/underscores; no '
                'hyphens/spaces). Current value: %r') % (self.db_name,))
        if self.provision_state == 'provisioned':
            raise UserError(_('This tenant is already provisioned.'))
        if not self.domain_ids.filtered(lambda d: d.active):
            raise UserError(_('Add at least one active domain before provisioning.'))

        job = self.env['tcrm.provisioning.job'].enqueue_for_tenant(self, db_name)
        self.write({'provision_state': 'queued'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tcrm.provisioning.job',
            'res_id': job.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_provisioning_jobs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Provisioning Jobs'),
            'res_model': 'tcrm.provisioning.job',
            'view_mode': 'list,form',
            'domain': [('tenant_id', '=', self.id)],
            'context': {'default_tenant_id': self.id},
        }
