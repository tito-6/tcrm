# -*- coding: utf-8 -*-
from tcrm import http, _
from tcrm.http import request
from tcrm.exceptions import UserError, AccessError


class MasterProvisioningApi(http.Controller):
    """Command Center endpoints for one-screen tenant provisioning."""

    def _check_master_access(self):
        user = request.env.user
        if not user.has_group('base.group_system'):
            raise AccessError(_('Only system administrators can provision tenants.'))

    @http.route('/tcrm_master/tenant/create_and_provision', type='jsonrpc', auth='user')
    def create_and_provision(self, name, domain, db_name, admin_login='admin',
                             admin_password='', client_name='', sector_id=False,
                             support_email='', support_phone=''):
        """Create tenant + primary domain + queue provisioning in one call."""
        self._check_master_access()
        env = request.env
        try:
            result = env['tcrm.tenant'].sudo().action_create_and_provision({
                'name': name,
                'domain': domain,
                'db_name': db_name,
                'admin_login': admin_login,
                'admin_password': admin_password,
                'client_name': client_name,
                'sector_id': sector_id,
                'support_email': support_email,
                'support_phone': support_phone,
            })
            return result
        except UserError as exc:
            return {'error': str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {'error': _('Provisioning request failed: %s') % exc}

    @http.route('/tcrm_master/provisioning/job_status', type='jsonrpc', auth='user')
    def job_status(self, job_id):
        """Poll a provisioning job (credentials visible to system admins only)."""
        self._check_master_access()
        job = request.env['tcrm.provisioning.job'].sudo().browse(int(job_id))
        if not job.exists():
            return {'error': _('Job not found')}
        return {
            'id': job.id,
            'state': job.state,
            'db_name': job.db_name,
            'tenant_id': job.tenant_id.id,
            'tenant_name': job.tenant_id.name,
            'error': job.error or '',
            'admin_login': job.admin_login or '',
            'admin_password': job.admin_password or '',
            'provision_state': job.tenant_id.provision_state,
        }
