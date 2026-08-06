# -*- coding: utf-8 -*-
import logging
import re
import secrets

from tcrm import models, fields, api, _
from tcrm.exceptions import UserError, ValidationError

from . import provisioning_common as pc

_logger = logging.getLogger(__name__)

STATES = [
    ('draft', 'Draft'),
    ('queued', 'Queued'),
    ('running', 'Running'),
    ('succeeded', 'Succeeded'),
    ('failed', 'Failed'),
    ('cancelled', 'Cancelled'),
]

# Default, version-locked module set installed into every new tenant DB.
# Overridable ONLY server-side via ir.config_parameter 'tcrm_provisioning.module_set'.
# Tenant DBs get the product stack — not the master Command Center module.
DEFAULT_MODULE_SET = (
    'base,web,mail,contacts,crm,'
    'tcrm_propertio,tcrm_call_center,tcrm_web_enhance'
)


class TcrmProvisioningJob(models.Model):
    _name = 'tcrm.provisioning.job'
    _description = 'TCRM Tenant Provisioning Job'
    _order = 'id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    tenant_id = fields.Many2one(
        'tcrm.tenant', string='Tenant', required=True, ondelete='cascade', index=True)
    db_name = fields.Char(string='Database Name', required=True, readonly=True,
                          help='Validated server-side; never taken from browser input.')
    module_set = fields.Text(string='Module Set', readonly=True,
                             help='Version-locked module list resolved server-side.')
    state = fields.Selection(STATES, default='draft', required=True, index=True, tracking=True)
    nonce = fields.Char(readonly=True)
    token = fields.Char(readonly=True, groups='base.group_system',
                        help='HMAC proving the job was minted by the control plane.')
    attempts = fields.Integer(default=0, readonly=True)
    max_attempts = fields.Integer(default=3)
    worker_host = fields.Char(readonly=True)
    started_at = fields.Datetime(readonly=True)
    finished_at = fields.Datetime(readonly=True)
    log = fields.Text(readonly=True)
    error = fields.Text(readonly=True)
    admin_login = fields.Char(readonly=True, groups='base.group_system')
    admin_password = fields.Char(
        string='Initial Admin Password', readonly=True, groups='base.group_system',
        help='Server-generated one-time password for the tenant administrator. '
             'Share securely with the tenant and rotate on first login.')
    admin_login_display = fields.Char(
        string='Admin Login', compute='_compute_admin_display',
        groups='base.group_system')
    admin_password_display = fields.Char(
        string='Initial Admin Password', compute='_compute_admin_display',
        groups='base.group_system')

    @api.depends('tenant_id', 'db_name', 'state')
    def _compute_display_name(self):
        for r in self:
            r.display_name = 'PROV/%s/%s [%s]' % (
                r.tenant_id.id or '-', r.db_name or '-', r.state)

    @api.depends('admin_login', 'admin_password')
    def _compute_admin_display(self):
        placeholder = _('Generated after successful provisioning')
        for r in self:
            r.admin_login_display = r.admin_login or placeholder
            r.admin_password_display = r.admin_password or placeholder

    # ------------------------------------------------------------------ helpers
    @api.model
    def _signing_secret(self):
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        if not secret:
            raise UserError(_('Missing database.secret; cannot sign provisioning jobs.'))
        return secret

    @api.model
    def _resolve_module_set(self):
        """Server-side, version-locked module set. Never from browser input."""
        raw = self.env['ir.config_parameter'].sudo().get_param(
            'tcrm_provisioning.module_set', DEFAULT_MODULE_SET)
        # Validate + normalise; raises on any bad token.
        return ','.join(pc.parse_module_set(raw))

    def verify_token(self):
        self.ensure_one()
        return pc.verify_job(self._signing_secret(), self.token,
                             self.tenant_id.id, self.db_name, self.nonce)

    # ------------------------------------------------------------------ minting
    @api.model
    def _validate_admin_credentials(self, admin_login, admin_password):
        """Validate operator-supplied tenant admin credentials (control plane only)."""
        login = (admin_login or '').strip()
        password = admin_password or ''
        if not login:
            raise UserError(_('Admin username is required.'))
        if len(login) < 3 or len(login) > 64:
            raise UserError(_('Admin username must be 3-64 characters.'))
        if not re.match(r'^[a-zA-Z0-9._@+-]+$', login):
            raise UserError(_(
                'Admin username may only contain letters, digits, and . _ @ + -'))
        if len(password) < 8:
            raise UserError(_('Admin password must be at least 8 characters.'))
        if len(password) > 128:
            raise UserError(_('Admin password is too long.'))
        return login, password

    @api.model
    def enqueue_for_tenant(self, tenant, db_name, admin_login=None, admin_password=None):
        """Mint a signed, queued provisioning job. Called by the control plane
        (tenant action / Master create screen) — NOT by anonymous web input.

        Optional admin_login/admin_password are stored on the job and applied by
        the privileged worker after the tenant DB is created.
        """
        try:
            pc.validate_db_name(db_name)  # raises ValueError on bad input
        except ValueError as exc:
            raise UserError(str(exc)) from exc
        # Reject duplicate DB mapping across tenants (defense in depth; the tenant
        # model also constrains this).
        dup = self.env['tcrm.tenant'].sudo().search_count(
            [('db_name', '=', db_name), ('id', '!=', tenant.id)])
        if dup:
            raise UserError(_('Database name %s is already mapped to another tenant.') % db_name)
        # No concurrent active job for the same tenant.
        active = self.sudo().search_count([
            ('tenant_id', '=', tenant.id), ('state', 'in', ('queued', 'running'))])
        if active:
            raise UserError(_('A provisioning job is already queued/running for this tenant.'))

        vals = {
            'tenant_id': tenant.id,
            'db_name': db_name,
            'module_set': self._resolve_module_set(),
            'nonce': secrets.token_hex(16),
            'state': 'queued',
        }
        if admin_login or admin_password:
            login, password = self._validate_admin_credentials(admin_login, admin_password)
            vals['admin_login'] = login
            vals['admin_password'] = password
        vals['token'] = pc.sign_job(
            self._signing_secret(), tenant.id, db_name, vals['nonce'])
        job = self.sudo().create(vals)
        _logger.info('Provisioning job %s queued for tenant %s (db=%s)',
                     job.id, tenant.id, db_name)
        return job

    # ------------------------------------------------------------------ worker API
    @api.model
    def claim_next(self, worker_host=None):
        """Atomically claim the oldest queued job and mark it running.

        Uses ``FOR UPDATE SKIP LOCKED`` so concurrent workers never grab the same
        job. Returns the claimed job record or an empty recordset."""
        self.env.cr.execute("""
            SELECT id FROM tcrm_provisioning_job
             WHERE state = 'queued'
             ORDER BY id ASC
             FOR UPDATE SKIP LOCKED
             LIMIT 1
        """)
        row = self.env.cr.fetchone()
        if not row:
            return self.browse()
        job = self.browse(row[0])
        job.write({
            'state': 'running',
            'attempts': job.attempts + 1,
            'worker_host': worker_host or 'worker',
            'started_at': fields.Datetime.now(),
            'error': False,
        })
        # Verify the signature before the worker acts on it.
        if not job.verify_token():
            job.write({'state': 'failed',
                       'error': 'Invalid job signature; refusing to provision.',
                       'finished_at': fields.Datetime.now()})
            _logger.error('Provisioning job %s failed signature verification', job.id)
            return self.browse()
        return job

    def mark_succeeded(self, log=None, admin_login=None, admin_password=None):
        self.ensure_one()
        vals = {'state': 'succeeded', 'finished_at': fields.Datetime.now()}
        if log:
            vals['log'] = (self.log or '') + '\n' + log
        if admin_login:
            vals['admin_login'] = admin_login
        if admin_password:
            vals['admin_password'] = admin_password
        self.write(vals)
        # Mirror provisioned modules into Master Access Management entitlements.
        try:
            tenant = self.tenant_id
            if tenant:
                names = [n.strip() for n in (self.module_set or '').split(',') if n.strip()]
                tenant._ensure_default_subscription('growth')
                tenant._sync_entitlements_from_module_names(names, source='provision')
        except Exception:  # noqa: BLE001
            _logger.exception(
                'Failed syncing entitlements after provision success job=%s', self.id)

    def mark_failed(self, error, log=None):
        self.ensure_one()
        vals = {'state': 'failed', 'error': (error or '')[:8000],
                'finished_at': fields.Datetime.now()}
        if log:
            vals['log'] = (self.log or '') + '\n' + log
        self.write(vals)

    def append_log(self, line):
        self.ensure_one()
        self.write({'log': (self.log or '') + '\n' + line})

    # ------------------------------------------------------------------ UI actions
    def action_cancel(self):
        for job in self:
            if job.state in ('succeeded',):
                raise UserError(_('Cannot cancel a completed job.'))
            job.write({'state': 'cancelled', 'finished_at': fields.Datetime.now()})
        return True

    def action_retry(self):
        """Idempotent retry: re-queue a failed job if attempts remain."""
        for job in self:
            if job.state not in ('failed', 'cancelled'):
                raise UserError(_('Only failed/cancelled jobs can be retried.'))
            if job.attempts >= job.max_attempts:
                raise UserError(_('Maximum provisioning attempts reached for this job.'))
            # Re-mint nonce/token so a stale token cannot be replayed.
            # Refresh module_set from current server-side config.
            nonce = secrets.token_hex(16)
            token = pc.sign_job(job._signing_secret(), job.tenant_id.id, job.db_name, nonce)
            job.write({
                'state': 'queued',
                'nonce': nonce,
                'token': token,
                'module_set': self._resolve_module_set(),
                'error': False,
                'started_at': False,
                'finished_at': False,
            })
        return True

    @api.constrains('db_name')
    def _check_db_name(self):
        for job in self:
            if not pc.is_valid_db_name(job.db_name):
                raise ValidationError(_('Invalid provisioning database name: %s') % job.db_name)
