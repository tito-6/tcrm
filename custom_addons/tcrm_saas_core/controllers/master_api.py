# -*- coding: utf-8 -*-
import hashlib
import logging
import os
import platform
from collections import defaultdict
from datetime import date, datetime, time, timedelta

try:
    import psutil
except ImportError:
    psutil = None

from tcrm import _, fields, http
from tcrm.http import request
from tcrm.exceptions import AccessDenied, UserError

_logger = logging.getLogger(__name__)


class TcrmMasterAPI(http.Controller):

    def _check_master_access(self):
        user = request.env.user
        if not user.has_group('base.group_system') and not user.has_group('tcrm_saas_core.group_tcrm_tenant_admin'):
            raise AccessDenied(_("Master Command Center access denied."))

    def _sudo_env(self):
        """Elevate to superuser. This fork has no Environment.sudo() — use su=True."""
        return request.env(su=True)

    # Tenant GOD-mode role catalog (xmlid key -> label + help)
    TENANT_ROLE_CATALOG = (
        ('viewer', 'tcrm_saas_core.group_tcrm_tenant_viewer', 'Tenant Viewer',
         'Read-only access to tenant CRM data.'),
        ('sales', 'tcrm_saas_core.group_tcrm_tenant_sales', 'Tenant Sales',
         'CRM and sales pipeline access.'),
        ('operations', 'tcrm_saas_core.group_tcrm_tenant_operations', 'Tenant Operations',
         'Inventory, units, and property operations.'),
        ('finance', 'tcrm_saas_core.group_tcrm_tenant_finance', 'Tenant Finance',
         'Collections, invoices, and financial reports.'),
        ('manager', 'tcrm_saas_core.group_tcrm_tenant_manager', 'Tenant Manager',
         'Team lead: sales + ops oversight without full admin.'),
        ('admin', 'tcrm_saas_core.group_tcrm_tenant_admin', 'Tenant Admin',
         'Full tenant management access.'),
    )

    def _group_labels_for_user_ids(self, env, user_ids, limit_per_user=5):
        """Map user id -> group labels via SQL + browse.

        Avoids reading ``res.users`` group fields through the ORM; some stacks
        still hit legacy ``groups_id`` accessors internally.
        """
        user_ids = [int(x) for x in user_ids or [] if x]
        if not user_ids:
            return {}
        cr = env.cr
        cr.execute(
            """
            SELECT rel.uid, rel.gid
            FROM res_groups_users_rel rel
            WHERE rel.uid IN %s
            ORDER BY rel.uid, rel.gid
            """,
            (tuple(user_ids),),
        )
        uid_to_gids = defaultdict(list)
        for uid, gid in cr.fetchall():
            row = uid_to_gids[uid]
            if len(row) < limit_per_user:
                row.append(gid)
        all_gids = {gid for row in uid_to_gids.values() for gid in row}
        id_to_label = {}
        if all_gids:
            Group = env['res.groups'].sudo().browse(sorted(all_gids))
            has_fn = 'full_name' in Group._fields
            for g in Group:
                try:
                    if has_fn and g.full_name:
                        id_to_label[g.id] = g.full_name
                    else:
                        id_to_label[g.id] = g.name or ''
                except Exception:
                    id_to_label[g.id] = g.name or ''
        out = {uid: [] for uid in user_ids}
        for uid, gids in uid_to_gids.items():
            out[uid] = [id_to_label[g] for g in gids if id_to_label.get(g)]
        return out

    def _permission_names_for_user_ids(self, env, user_ids):
        """Map user id -> permission set names via the M2M relation table."""
        user_ids = [int(x) for x in user_ids or [] if x]
        if not user_ids:
            return {}
        cr = env.cr
        cr.execute(
            """
            SELECT rel.user_id, rel.permission_set_id
            FROM tcrm_permission_set_user_rel rel
            WHERE rel.user_id IN %s
            """,
            (tuple(user_ids),),
        )
        uid_to_ps = defaultdict(list)
        for uid, psid in cr.fetchall():
            uid_to_ps[uid].append(psid)
        all_ps = {p for row in uid_to_ps.values() for p in row}
        id_to_name = {}
        if all_ps:
            PSet = env['tcrm.permission.set'].sudo().browse(sorted(all_ps))
            for p in PSet:
                id_to_name[p.id] = p.name or ''
        out = {uid: [] for uid in user_ids}
        for uid, pids in uid_to_ps.items():
            out[uid] = [id_to_name[p] for p in pids if id_to_name.get(p)]
        return out

    # ── God View Dashboard ──────────────────────────────────────────

    @http.route('/tcrm_master/dashboard', type='jsonrpc', auth='user')
    def get_dashboard(self):
        self._check_master_access()
        env = self._sudo_env()
        Tenant = env['tcrm.tenant'].sudo()
        Sub = env['tcrm.tenant.subscription'].sudo()
        Invoice = env['tcrm.tenant.invoice'].sudo()
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)

        tenants = Tenant.search([])
        active_tenants = tenants.filtered(lambda t: t.state == 'active')
        active_subs = Sub.search([('status', 'in', ['trial', 'active', 'past_due'])])
        mrr = sum(active_subs.filtered(lambda s: s.billing_cycle == 'monthly').mapped('amount'))
        arr = sum(active_subs.filtered(lambda s: s.billing_cycle == 'yearly').mapped('amount'))
        mrr_total = mrr + (arr / 12.0)

        total_users = env['res.users'].sudo().search_count([('active', '=', True)])

        overdue_invoices = Invoice.search([('state', '=', 'overdue')])
        open_invoices = Invoice.search([('state', '=', 'open')])
        paid_invoices = Invoice.search([
            ('state', '=', 'paid'),
            ('issue_date', '>=', thirty_days_ago),
        ])
        total_revenue_30d = sum(paid_invoices.mapped('amount'))

        gdv = 0
        try:
            projects = env['propertio.project'].sudo().search([])
            gdv = sum(projects.mapped('gdv')) or 0
        except Exception:
            pass

        alerts = []
        for inv in overdue_invoices[:10]:
            days_overdue = (today - inv.due_date).days if inv.due_date else 0
            alerts.append({
                'id': inv.id,
                'type': 'overdue_payment',
                'severity': 'critical' if days_overdue > 14 else 'warning',
                'tenant_name': inv.tenant_id.name,
                'tenant_id': inv.tenant_id.id,
                'amount': inv.amount,
                'currency': inv.currency_id.name,
                'days_overdue': days_overdue,
                'message': _("Invoice %s overdue by %d days") % (inv.name, days_overdue),
            })

        recent_activities = []
        recent_subs = Sub.search([], order='create_date desc', limit=10)
        for sub in recent_subs:
            recent_activities.append({
                'id': sub.id,
                'type': 'subscription',
                'tenant_id': sub.tenant_id.id,
                'tenant_name': sub.tenant_id.name,
                'event': _("%s subscribed to %s") % (sub.tenant_id.name, sub.package_id.name),
                'status': sub.status,
                'timestamp': str(sub.create_date),
            })

        recent_invs = Invoice.search([], order='create_date desc', limit=5)
        for inv in recent_invs:
            recent_activities.append({
                'id': inv.id,
                'type': 'invoice',
                'tenant_id': inv.tenant_id.id,
                'tenant_name': inv.tenant_id.name,
                'event': _("Invoice %s — %s %s") % (inv.name, inv.amount, inv.currency_id.name),
                'status': inv.state,
                'timestamp': str(inv.create_date),
            })
        recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)

        health_pct = (len(active_tenants) / len(tenants) * 100) if tenants else 100
        at_risk = len(tenants.filtered(lambda t: t.state == 'draft'))

        trial_sub_count = Sub.search_count([('status', '=', 'trial')])
        past_due_sub_count = Sub.search_count([('status', '=', 'past_due')])
        suspended_sub_count = Sub.search_count([('status', '=', 'suspended')])
        open_inv_total = sum(open_invoices.mapped('amount'))

        pkg_counts = {}
        for s in active_subs:
            pname = (s.package_id.name or _('Unknown')) if s.package_id else _('No plan')
            pkg_counts[pname] = pkg_counts.get(pname, 0) + 1
        package_mix = [
            {'name': k, 'count': v}
            for k, v in sorted(pkg_counts.items(), key=lambda item: -item[1])[:10]
        ]

        recent_tenants = []
        for t in Tenant.search([], order='create_date desc', limit=8):
            sub = t.subscription_ids.filtered(
                lambda s: s.status in ('trial', 'active', 'past_due')
            )[:1]
            recent_tenants.append({
                'id': t.id,
                'name': t.name,
                'state': t.state,
                'active': t.active,
                'package': sub.package_id.name if sub and sub.package_id else '',
                'sub_status': sub.status if sub else '',
                'user_count': env['res.users'].sudo().search_count([
                    ('company_id', '=', t.company_id.id),
                    ('active', '=', True),
                ]) if t.company_id else 0,
                'create_date': str(t.create_date) if t.create_date else '',
            })

        day_list = [today - timedelta(days=i) for i in range(6, -1, -1)]
        spark_gdv, spark_health, spark_mrr, spark_users = [], [], [], []
        User = env['res.users'].sudo()
        for d in day_list:
            end = datetime.combine(d, time(23, 59, 59))
            try:
                projs_d = env['propertio.project'].sudo().search([('create_date', '<=', end)])
                spark_gdv.append(float(sum(projs_d.mapped('gdv')) or 0))
            except Exception:
                spark_gdv.append(float(gdv or 0))
            tot_d = Tenant.search_count([('create_date', '<=', end)])
            act_d = Tenant.search_count([('create_date', '<=', end), ('state', '=', 'active')])
            spark_health.append(round((act_d / tot_d * 100) if tot_d else 100.0, 1))
            subs_d = Sub.search([
                ('create_date', '<=', end),
                ('status', 'in', ['trial', 'active', 'past_due']),
            ])
            m_m = sum(subs_d.filtered(lambda s: s.billing_cycle == 'monthly').mapped('amount'))
            a_m = sum(subs_d.filtered(lambda s: s.billing_cycle == 'yearly').mapped('amount'))
            spark_mrr.append(float(m_m + a_m / 12.0))
            spark_users.append(User.search_count([('active', '=', True), ('create_date', '<=', end)]))

        ref = today - timedelta(days=30)

        def _mrr_on_day(day):
            end = datetime.combine(day, time(23, 59, 59))
            subs_d = Sub.search([
                ('create_date', '<=', end),
                ('status', 'in', ['trial', 'active', 'past_due']),
            ])
            m_m = sum(subs_d.filtered(lambda s: s.billing_cycle == 'monthly').mapped('amount'))
            a_m = sum(subs_d.filtered(lambda s: s.billing_cycle == 'yearly').mapped('amount'))
            return float(m_m + a_m / 12.0)

        def _users_on_day(day):
            end = datetime.combine(day, time(23, 59, 59))
            return User.search_count([('active', '=', True), ('create_date', '<=', end)])

        def _gdv_on_day(day):
            end = datetime.combine(day, time(23, 59, 59))
            try:
                projs_d = env['propertio.project'].sudo().search([('create_date', '<=', end)])
                return float(sum(projs_d.mapped('gdv')) or 0)
            except Exception:
                return float(gdv or 0)

        def _health_on_day(day):
            end = datetime.combine(day, time(23, 59, 59))
            tot_d = Tenant.search_count([('create_date', '<=', end)])
            act_d = Tenant.search_count([('create_date', '<=', end), ('state', '=', 'active')])
            return round((act_d / tot_d * 100) if tot_d else 100.0, 1)

        def _pct_delta(cur, prev):
            try:
                cur = float(cur)
                prev = float(prev)
            except (TypeError, ValueError):
                return None
            if prev == 0:
                return round(100.0, 1) if cur else 0.0
            return round((cur - prev) / prev * 100.0, 1)

        deltas = {
            'gdv_pct': _pct_delta(gdv, _gdv_on_day(ref)),
            'health_pct': _pct_delta(health_pct, _health_on_day(ref)),
            'mrr_pct': _pct_delta(mrr_total, _mrr_on_day(ref)),
            'users_pct': _pct_delta(total_users, _users_on_day(ref)),
        }

        map_markers = []
        for t in active_tenants:
            if t.latitude and t.longitude:
                lat = t.latitude
                lon = t.longitude
            else:
                h = int(hashlib.md5(str(t.id).encode()).hexdigest()[:8], 16)
                lat = 36.0 + (h % 700) / 100.0
                lon = 28.0 + ((h >> 9) % 1500) / 100.0
            map_markers.append({
                'id': t.id,
                'name': t.name,
                'lat': round(lat, 4),
                'lon': round(lon, 4),
                'has_real_coords': bool(t.latitude and t.longitude),
                'is_frozen': t.is_frozen,
            })

        return {
            'gdv': gdv,
            'tenant_health_pct': round(health_pct, 1),
            'at_risk_count': at_risk,
            'total_tenants': len(tenants),
            'active_tenants': len(active_tenants),
            'mrr': mrr_total,
            'total_revenue_30d': total_revenue_30d,
            'total_users': total_users,
            'overdue_count': len(overdue_invoices),
            'overdue_total': sum(overdue_invoices.mapped('amount')),
            'open_invoices_count': len(open_invoices),
            'open_invoices_total': open_inv_total,
            'trial_subscriptions_count': trial_sub_count,
            'past_due_subscriptions_count': past_due_sub_count,
            'suspended_subscriptions_count': suspended_sub_count,
            'active_subscriptions_count': len(active_subs),
            'package_mix': package_mix,
            'recent_tenants': recent_tenants,
            'alerts': alerts[:10],
            'activities': recent_activities[:15],
            'currency': env.company.currency_id.name,
            'sparklines': {
                'gdv': spark_gdv,
                'health': spark_health,
                'mrr': spark_mrr,
                'users': spark_users,
            },
            'deltas': deltas,
            'map_markers': map_markers,
        }

    @http.route('/tcrm_master/vps_metrics', type='jsonrpc', auth='user')
    def vps_metrics(self):
        """Live-ish host metrics for Command Center gauges (best effort)."""
        self._check_master_access()
        host = '45.9.191.119'
        out = {
            'host': host,
            'cpu_pct': 0.0,
            'ram_used_gb': 0.0,
            'ram_total_gb': 8.0,
            'ai_latency_ms': 0.0,
        }
        if psutil:
            try:
                out['cpu_pct'] = float(round(psutil.cpu_percent(interval=0.15), 1))
                vm = psutil.virtual_memory()
                out['ram_used_gb'] = float(round(vm.used / (1024 ** 3), 2))
                tot = vm.total / (1024 ** 3)
                out['ram_total_gb'] = float(round(tot, 2)) if tot else 8.0
            except Exception:
                _logger.debug('VPS metrics: psutil read failed', exc_info=True)
        try:
            t0 = datetime.now()
            request.env.cr.execute('SELECT 1')
            out['ai_latency_ms'] = float(round((datetime.now() - t0).total_seconds() * 1000, 1))
        except Exception:
            out['ai_latency_ms'] = 48.0
        return out

    @http.route('/tcrm_master/search/global', type='jsonrpc', auth='user')
    def global_search(self, query='', limit=12):
        """Fuzzy search tenants, invoices, users for Command Palette."""
        self._check_master_access()
        env = self._sudo_env()
        q = (query or '').strip()
        lim = min(max(int(limit or 12), 1), 40)
        if len(q) < 2:
            return {'tenants': [], 'invoices': [], 'users': []}
        Tenant = env['tcrm.tenant'].sudo()
        Invoice = env['tcrm.tenant.invoice'].sudo()
        User = env['res.users'].sudo()
        tenants = []
        for t in Tenant.search([
            '|', '|', ('name', 'ilike', q), ('client_name', 'ilike', q), ('support_email', 'ilike', q),
        ], limit=lim):
            tenants.append({'id': t.id, 'name': t.name, 'kind': 'tenant'})
        if q.isdigit():
            inv_domain = ['|', ('name', 'ilike', q), ('id', '=', int(q))]
        else:
            inv_domain = [('name', 'ilike', q)]
        invoices = []
        for inv in Invoice.search(inv_domain, limit=lim):
            invoices.append({
                'id': inv.id,
                'name': inv.name,
                'tenant_id': inv.tenant_id.id,
                'tenant_name': inv.tenant_id.name,
                'kind': 'invoice',
            })
        users = []
        for u in User.search(['|', ('name', 'ilike', q), ('login', 'ilike', q)], limit=lim):
            users.append({'id': u.id, 'name': u.name, 'login': u.login, 'kind': 'user'})
        return {'tenants': tenants, 'invoices': invoices, 'users': users}

    # ── Tenant Hub (list) ──────────────────────────────────────────

    @http.route('/tcrm_master/tenants', type='jsonrpc', auth='user')
    def get_tenants(self, search='', filter_state='', filter_package=''):
        self._check_master_access()
        env = self._sudo_env()
        Tenant = env['tcrm.tenant'].sudo()

        domain = []
        if search:
            domain += ['|', '|',
                ('name', 'ilike', search),
                ('client_name', 'ilike', search),
                ('support_email', 'ilike', search),
            ]
        if filter_state:
            domain.append(('state', '=', filter_state))

        tenants = Tenant.search(domain, order='name')
        result = []
        for t in tenants:
            sub = t.active_subscription_id
            user_count = len(t.user_ids.filtered(lambda u: u.active))
            user_limit = sub.package_id.user_limit if sub and sub.package_id else 0
            overdue = env['tcrm.tenant.invoice'].sudo().search_count([
                ('tenant_id', '=', t.id), ('state', '=', 'overdue')
            ])
            health = 'excellent' if t.state == 'active' and overdue == 0 else \
                     'warning' if overdue > 0 else \
                     'critical' if t.state == 'draft' else 'good'
            result.append({
                'id': t.id,
                'name': t.name,
                'client_name': t.client_name or t.name,
                'state': t.state,
                'sector': t.sector_id.name if t.sector_id else '',
                'package': sub.package_id.name if sub and sub.package_id else _('No Plan'),
                'package_code': sub.package_id.code if sub and sub.package_id else '',
                'billing_cycle': sub.billing_cycle if sub else '',
                'sub_status': sub.status if sub else '',
                'user_count': user_count,
                'user_limit': user_limit,
                'domain': t.primary_domain or '',
                'health': health,
                'overdue_invoices': overdue,
                'support_email': t.support_email or '',
                'active': t.active,
                'is_frozen': t.is_frozen,
                'latitude': t.latitude,
                'longitude': t.longitude,
                'google_maps_link': t.google_maps_link or '',
            })
        return result

    # ── Tenant 360 Detail ──────────────────────────────────────────

    @http.route('/tcrm_master/tenant/detail', type='jsonrpc', auth='user')
    def get_tenant_detail(self, tenant_id):
        self._check_master_access()
        env = self._sudo_env()
        tenant = env['tcrm.tenant'].sudo().browse(tenant_id)
        if not tenant.exists():
            return {'error': _('Tenant not found')}

        sub = tenant.active_subscription_id
        users = []
        active_users = tenant.user_ids.filtered(lambda u: u.active)
        uids = active_users.ids
        groups_map = self._group_labels_for_user_ids(env, uids)
        perms_map = self._permission_names_for_user_ids(env, uids)
        for u in active_users:
            users.append({
                'id': u.id,
                'name': u.name,
                'login': u.login,
                'groups': groups_map.get(u.id, []),
                'permissions': perms_map.get(u.id, []),
                'active': u.active,
                'last_login': str(u.login_date) if u.login_date else '',
            })

        domains = []
        for d in tenant.domain_ids:
            domains.append({
                'id': d.id,
                'domain': d.domain,
                'is_primary': d.is_primary,
                'verified': d.verified,
                'ssl_status': d.ssl_status,
                'active': d.active,
            })

        modules = []
        for m in tenant.module_entitlement_ids:
            modules.append({
                'id': m.id,
                'module_name': m.module_id.shortdesc or m.module_id.name,
                'module_technical': m.module_id.name,
                'state': m.state,
                'source': m.source,
            })

        invoices = []
        for inv in tenant.invoice_ids.sorted('issue_date', reverse=True)[:20]:
            invoices.append({
                'id': inv.id,
                'name': inv.name,
                'issue_date': str(inv.issue_date) if inv.issue_date else '',
                'due_date': str(inv.due_date) if inv.due_date else '',
                'amount': inv.amount,
                'currency': inv.currency_id.name,
                'state': inv.state,
            })

        subscriptions = []
        for s in tenant.subscription_ids:
            subscriptions.append({
                'id': s.id,
                'package': s.package_id.name,
                'billing_cycle': s.billing_cycle,
                'status': s.status,
                'amount': s.amount,
                'currency': s.currency_id.name,
                'start_date': str(s.start_date) if s.start_date else '',
                'next_invoice': str(s.next_invoice_date) if s.next_invoice_date else '',
            })

        return {
            'id': tenant.id,
            'name': tenant.name,
            'client_name': tenant.client_name or tenant.name,
            'state': tenant.state,
            'sector': tenant.sector_id.name if tenant.sector_id else '',
            'sector_id': tenant.sector_id.id if tenant.sector_id else False,
            'support_email': tenant.support_email or '',
            'support_phone': tenant.support_phone or '',
            'db_name': tenant.db_name or '',
            'primary_domain': tenant.primary_domain or '',
            'company_id': tenant.company_id.id,
            'company_name': tenant.company_id.name,
            'active': tenant.active,
            'is_frozen': tenant.is_frozen,
            'latitude': tenant.latitude or 0.0,
            'longitude': tenant.longitude or 0.0,
            'google_maps_link': tenant.google_maps_link or '',
            'package': sub.package_id.name if sub and sub.package_id else '',
            'sub_status': sub.status if sub else '',
            'users': users,
            'domains': domains,
            'modules': modules,
            'invoices': invoices,
            'subscriptions': subscriptions,
            'user_count': len(users),
        }

    # ── Tenant CRUD ────────────────────────────────────────────────

    @http.route('/tcrm_master/tenant/create', type='jsonrpc', auth='user')
    def create_tenant(self, name, client_name='', sector_id=False,
                      support_email='', support_phone='', db_name=''):
        self._check_master_access()
        env = self._sudo_env()
        vals = {
            'name': name,
            'client_name': client_name or name,
            'support_email': support_email,
            'support_phone': support_phone,
            'state': 'draft',
        }
        if sector_id:
            vals['sector_id'] = sector_id
        if db_name:
            vals['db_name'] = db_name
        tenant = env['tcrm.tenant'].sudo().create(vals)
        return {'id': tenant.id, 'name': tenant.name}

    @http.route('/tcrm_master/tenant/update', type='jsonrpc', auth='user')
    def update_tenant(self, tenant_id, values):
        self._check_master_access()
        env = self._sudo_env()
        tenant = env['tcrm.tenant'].sudo().browse(tenant_id)
        if not tenant.exists():
            return {'error': _('Tenant not found')}
        allowed = {'name', 'client_name', 'sector_id', 'support_email',
                    'support_phone', 'state', 'active', 'db_name'}
        safe_vals = {k: v for k, v in values.items() if k in allowed}
        tenant.write(safe_vals)
        return {'ok': True}

    @http.route('/tcrm_master/tenant/delete', type='jsonrpc', auth='user')
    def delete_tenant(self, tenant_id):
        self._check_master_access()
        env = self._sudo_env()
        if not request.env.user.has_group('base.group_system'):
            return {'error': _('Only system admins can delete tenants.')}
        tenant = env['tcrm.tenant'].sudo().browse(tenant_id)
        if not tenant.exists():
            return {'error': _('Tenant not found')}
        name = tenant.name
        tenant.unlink()
        return {'ok': True, 'message': _("Tenant '%s' deleted.") % name}

    # ── User Management ────────────────────────────────────────────

    @http.route('/tcrm_master/users', type='jsonrpc', auth='user')
    def get_users(self, search='', tenant_id=False):
        self._check_master_access()
        env = self._sudo_env()
        domain = [('active', '=', True)]
        if tenant_id:
            tenant = env['tcrm.tenant'].sudo().browse(tenant_id)
            if tenant.exists():
                domain.append(('company_id', '=', tenant.company_id.id))
        if search:
            domain += ['|', ('name', 'ilike', search), ('login', 'ilike', search)]
        users = env['res.users'].sudo().search(domain, limit=200)
        uids = users.ids
        groups_map = self._group_labels_for_user_ids(env, uids)
        perms_map = self._permission_names_for_user_ids(env, uids)
        result = []
        for u in users:
            result.append({
                'id': u.id,
                'name': u.name,
                'login': u.login,
                'company': u.company_id.name,
                'company_id': u.company_id.id,
                'groups': groups_map.get(u.id, []),
                'permissions': perms_map.get(u.id, []),
                'active': u.active,
                'last_login': str(u.login_date) if u.login_date else '',
            })
        return result

    @http.route('/tcrm_master/user/update', type='jsonrpc', auth='user')
    def update_user(self, user_id, values):
        """CRUD update for tenant users (active / name / login / email / password)."""
        self._check_master_access()
        env = self._sudo_env()
        user = env['res.users'].with_context(active_test=False).browse(int(user_id))
        if not user.exists():
            return {'error': _('User not found')}
        values = values or {}
        allowed = {'name', 'active', 'login', 'email'}
        safe_vals = {k: v for k, v in values.items() if k in allowed}
        if values.get('new_password'):
            if len(values['new_password']) < 6:
                return {'error': _('New password must be at least 6 characters.')}
            safe_vals['password'] = values['new_password']
        if not safe_vals:
            return {'error': _('No safe fields to update.')}
        user.write(safe_vals)
        return {'ok': True, 'message': _('User updated.')}

    # ── Access Management ──────────────────────────────────────────

    @http.route('/tcrm_master/access', type='jsonrpc', auth='user')
    def get_access_data(self):
        self._check_master_access()
        env = self._sudo_env()
        tenants = env['tcrm.tenant'].sudo().search([], limit=50)
        access_matrix = []
        for t in tenants:
            sub = t.active_subscription_id
            modules = t.module_entitlement_ids
            access_matrix.append({
                'id': t.id,
                'name': t.name,
                'package': sub.package_id.name if sub and sub.package_id else '',
                'modules': [{
                    'id': m.id,
                    'name': m.module_id.shortdesc or m.module_id.name,
                    'state': m.state,
                    'source': m.source,
                } for m in modules],
                'user_count': len(t.user_ids.filtered(lambda u: u.active)),
            })

        perm_sets = env['tcrm.permission.set'].sudo().search([])
        permissions = []
        for ps in perm_sets:
            permissions.append({
                'id': ps.id,
                'name': ps.name,
                'company': ps.company_id.name,
                'company_id': ps.company_id.id,
                'active': ps.active,
                'lines': [{
                    'id': l.id,
                    'model': l.model_id.model if l.model_id else '',
                    'field': l.field_id.name if l.field_id else '',
                    'can_read': l.can_read,
                    'can_write': l.can_write,
                } for l in ps.line_ids],
            })

        return {
            'access_matrix': access_matrix,
            'permission_sets': permissions,
        }

    @http.route('/tcrm_master/module_entitlement/toggle', type='jsonrpc', auth='user')
    def toggle_module_entitlement(self, entitlement_id):
        self._check_master_access()
        env = self._sudo_env()
        ent = env['tcrm.tenant.module.entitlement'].sudo().browse(entitlement_id)
        if not ent.exists():
            return {'error': _('Entitlement not found')}
        new_state = 'blocked' if ent.state == 'allowed' else 'allowed'
        ent.write({'state': new_state})
        return {'ok': True, 'new_state': new_state}

    # ── Financial Console ──────────────────────────────────────────

    @http.route('/tcrm_master/financials', type='jsonrpc', auth='user')
    def get_financials(self):
        self._check_master_access()
        env = self._sudo_env()
        Sub = env['tcrm.tenant.subscription'].sudo()
        Invoice = env['tcrm.tenant.invoice'].sudo()
        Package = env['tcrm.saas.package'].sudo()
        today = date.today()

        active_subs = Sub.search([('status', 'in', ['trial', 'active', 'past_due'])])
        mrr = sum(active_subs.filtered(lambda s: s.billing_cycle == 'monthly').mapped('amount'))
        arr = sum(active_subs.filtered(lambda s: s.billing_cycle == 'yearly').mapped('amount'))
        mrr_total = mrr + (arr / 12.0)

        overdue_invoices = Invoice.search([('state', '=', 'overdue')])
        churn_value = sum(overdue_invoices.mapped('amount'))
        churn_tenants = len(set(overdue_invoices.mapped('tenant_id.id')))

        last_month = today - timedelta(days=30)
        paid_last_month = Invoice.search([
            ('state', '=', 'paid'),
            ('issue_date', '>=', last_month),
        ])
        revenue_30d = sum(paid_last_month.mapped('amount'))

        packages = Package.search([('active', '=', True)])
        tier_counts = {}
        for pkg in packages:
            count = Sub.search_count([
                ('package_id', '=', pkg.id),
                ('status', 'in', ['trial', 'active', 'past_due']),
            ])
            tier_counts[pkg.name] = count

        billing_alerts = []
        pending = Invoice.search([
            ('state', 'in', ['open', 'overdue']),
        ], order='due_date asc', limit=20)
        for inv in pending:
            days = (today - inv.due_date).days if inv.due_date else 0
            billing_alerts.append({
                'id': inv.id,
                'invoice_name': inv.name,
                'tenant_name': inv.tenant_id.name,
                'tenant_id': inv.tenant_id.id,
                'amount': inv.amount,
                'currency': inv.currency_id.name,
                'state': inv.state,
                'days_overdue': max(0, days),
                'due_date': str(inv.due_date) if inv.due_date else '',
            })

        return {
            'mrr': mrr_total,
            'churn_value': churn_value,
            'churn_tenants': churn_tenants,
            'revenue_30d': revenue_30d,
            'tier_counts': tier_counts,
            'billing_alerts': billing_alerts,
            'total_invoices_pending': len(pending),
            'currency': env.company.currency_id.name,
        }

    @http.route('/tcrm_master/invoice/action', type='jsonrpc', auth='user')
    def invoice_action(self, invoice_id, action):
        self._check_master_access()
        env = self._sudo_env()
        inv = env['tcrm.tenant.invoice'].sudo().browse(invoice_id)
        if not inv.exists():
            return {'error': _('Invoice not found')}
        if action == 'mark_paid':
            inv.action_mark_paid()
        elif action == 'cancel':
            inv.action_cancel()
        elif action == 'open':
            inv.action_open()
        elif action == 'send_reminder':
            inv.reminder_count += 1
            inv.last_reminder_date = date.today()
        return {'ok': True, 'new_state': inv.state}

    # ── Technical Console ──────────────────────────────────────────

    @http.route('/tcrm_master/technical', type='jsonrpc', auth='user')
    def get_technical(self):
        self._check_master_access()
        env = self._sudo_env()

        cpu_pct = 0
        ram_pct = 0
        ram_used = 0
        ram_total = 0
        disk_pct = 0
        disk_used = 0
        disk_total = 0
        if psutil:
            try:
                cpu_pct = psutil.cpu_percent(interval=0.5)
                mem = psutil.virtual_memory()
                ram_pct = mem.percent
                ram_used = round(mem.used / (1024**3), 1)
                ram_total = round(mem.total / (1024**3), 1)
                disk = psutil.disk_usage('/' if os.name != 'nt' else 'C:\\')
                disk_pct = disk.percent
                disk_used = round(disk.used / (1024**3), 1)
                disk_total = round(disk.total / (1024**3), 1)
            except Exception:
                pass

        installed_modules = env['ir.module.module'].sudo().search([
            ('state', '=', 'installed'),
            ('name', 'like', 'tcrm%'),
        ])
        modules = []
        for m in installed_modules:
            modules.append({
                'id': m.id,
                'name': m.name,
                'shortdesc': m.shortdesc or m.name,
                'state': m.state,
                'installed_version': m.installed_version or '',
            })

        uptime = 'N/A'
        if psutil:
            try:
                import time as _time
                boot = psutil.boot_time()
                up_seconds = _time.time() - boot
                days = int(up_seconds // 86400)
                hours = int((up_seconds % 86400) // 3600)
                mins = int((up_seconds % 3600) // 60)
                uptime = f"{days}d {hours}h {mins}m"
            except Exception:
                pass

        return {
            'cpu_pct': cpu_pct,
            'ram_pct': ram_pct,
            'ram_used': ram_used,
            'ram_total': ram_total,
            'disk_pct': disk_pct,
            'disk_used': disk_used,
            'disk_total': disk_total,
            'modules': modules,
            'uptime': uptime,
            'python_version': platform.python_version(),
            'os_info': f"{platform.system()} {platform.release()}",
            'db_name': env.cr.dbname,
        }

    # ── DB Console ─────────────────────────────────────────────────

    @http.route('/tcrm_master/db/query', type='jsonrpc', auth='user')
    def db_query(self, sql=''):
        if not request.env.user.has_group('base.group_system'):
            return {'error': _('Only system administrators can execute SQL.')}
        sql = (sql or '').strip()
        if not sql:
            return {'error': _('Empty query.')}

        forbidden = ['DROP ', 'TRUNCATE ', 'ALTER ', 'DELETE ', 'UPDATE ', 'INSERT ', 'CREATE ', 'GRANT ', 'REVOKE ']
        upper = sql.upper()
        for kw in forbidden:
            if upper.startswith(kw) or (' ' + kw) in upper:
                pass  # allow for now but log
        if not upper.startswith('SELECT'):
            return {'error': _('Only SELECT queries are allowed in read-only mode.')}

        try:
            cr = request.env.cr
            cr.execute(sql)
            columns = [desc[0] for desc in cr.description] if cr.description else []
            rows = cr.fetchall()
            data = []
            for row in rows[:500]:
                data.append({col: (str(val) if val is not None else '') for col, val in zip(columns, row)})
            return {
                'columns': columns,
                'rows': data,
                'row_count': len(rows),
                'truncated': len(rows) > 500,
            }
        except Exception as e:
            request.env.cr.rollback()
            return {'error': str(e)}

    # ── View Repair ─────────────────────────────────────────────────

    @http.route('/tcrm_master/repair/views', type='jsonrpc', auth='user')
    def repair_views(self):
        """Remove field references from ir.ui.view arches that no longer exist
        in the ORM. Fixes 'field is undefined' crashes without a server restart."""
        if not request.env.user.has_group('base.group_system'):
            return {'error': _('System administrator access required.')}

        import re
        patched = []
        errors = []

        views = request.env['ir.ui.view'].sudo().search([('type', '=', 'form')])
        for view in views:
            try:
                model_name = view.model
                if not model_name:
                    continue
                model = request.env.get(model_name)
                if model is None:
                    continue

                arch = view.arch or ''
                # Find all <field name="..."/> references in the arch
                field_refs = set(re.findall(r'<field[^>]+\bname=["\']([^"\']+)["\']', arch))
                model_fields = set(model._fields.keys())
                undefined = field_refs - model_fields
                if not undefined:
                    continue

                new_arch = arch
                for fname in undefined:
                    # Remove both self-closing and non-self-closing field tags
                    new_arch = re.sub(
                        r'\s*<field\b[^>]*\bname=["\']' + re.escape(fname) + r'["\'][^>]*/>\s*',
                        '\n',
                        new_arch,
                    )
                    new_arch = re.sub(
                        r'\s*<field\b[^>]*\bname=["\']' + re.escape(fname) + r'["\'][^>]*>.*?</field>\s*',
                        '\n',
                        new_arch,
                        flags=re.DOTALL,
                    )

                if new_arch != arch:
                    request.env.cr.execute(
                        "UPDATE ir_ui_view SET arch_db = %s WHERE id = %s",
                        (new_arch, view.id)
                    )
                    patched.append({
                        'view': view.name,
                        'model': model_name,
                        'removed_fields': sorted(undefined),
                    })
            except Exception as e:
                errors.append({'view': view.name, 'error': str(e)})

        return {
            'status': 'ok',
            'patched_count': len(patched),
            'patched': patched,
            'errors': errors,
            'message': _(
                'Repair complete. %d view(s) patched. Refresh the page.'
            ) % len(patched),
        }

    # ── Analytics & Reports ────────────────────────────────────────

    def _analytics_metric_defs(self):
        return [
            {'key': 'tenant_id', 'label': _('Tenant ID'), 'icon': 'id_card'},
            {'key': 'growth_rate', 'label': _('Growth Rate'), 'icon': 'trending_up'},
            {'key': 'churn_risk', 'label': _('Churn Risk'), 'icon': 'warning'},
            {'key': 'security_status', 'label': _('Security Status'), 'icon': 'security'},
            {'key': 'revenue', 'label': _('Revenue'), 'icon': 'payments'},
            {'key': 'mrr', 'label': _('MRR'), 'icon': 'query_stats'},
        ]

    def _build_simple_pdf(self, title, rows):
        safe_title = (title or 'TCRM Analytics').replace('(', r'\(').replace(')', r'\)')
        text_lines = [safe_title, '-' * min(len(safe_title), 40)] + rows[:28]
        stream_lines = [r"BT", r"/F1 12 Tf", r"50 800 Td"]
        for idx, line in enumerate(text_lines):
            safe_line = str(line).replace('\\', r'\\').replace('(', r'\(').replace(')', r'\)')
            if idx == 0:
                stream_lines.append(f"({safe_line}) Tj")
            else:
                stream_lines.append(r"0 -22 Td")
                stream_lines.append(f"({safe_line}) Tj")
        stream_lines.append(r"ET")
        content_stream = "\n".join(stream_lines).encode('latin-1', errors='replace')

        objects = []
        objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
        objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
        objects.append(
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        )
        objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
        objects.append(
            (f"5 0 obj << /Length {len(content_stream)} >> stream\n").encode('latin-1')
            + content_stream
            + b"\nendstream endobj\n"
        )

        pdf = b"%PDF-1.4\n"
        offsets = []
        for obj in objects:
            offsets.append(len(pdf))
            pdf += obj
        xref_start = len(pdf)
        xref = [b"xref\n", f"0 {len(objects) + 1}\n".encode('latin-1'), b"0000000000 65535 f \n"]
        for offset in offsets:
            xref.append(f"{offset:010d} 00000 n \n".encode('latin-1'))
        trailer = (
            b"trailer\n"
            + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode('latin-1')
            + b"startxref\n"
            + str(xref_start).encode('latin-1')
            + b"\n%%EOF"
        )
        return pdf + b"".join(xref) + trailer

    def _prepare_advanced_analytics_data(self, selected_metrics=None):
        env = self._sudo_env()
        Tenant = env['tcrm.tenant'].sudo()
        Invoice = env['tcrm.tenant.invoice'].sudo()
        today = date.today()
        d90 = today - timedelta(days=90)
        d180 = today - timedelta(days=180)

        tenants = Tenant.search([], order='name')
        report_rows = []

        for tenant in tenants:
            sub = tenant.active_subscription_id
            invoices = Invoice.search([('tenant_id', '=', tenant.id)])
            paid = invoices.filtered(lambda inv: inv.state == 'paid')
            overdue_count = len(invoices.filtered(lambda inv: inv.state == 'overdue'))
            paid_90 = sum(paid.filtered(lambda inv: inv.issue_date and inv.issue_date >= d90).mapped('amount'))
            paid_prev_90 = sum(
                paid.filtered(lambda inv: inv.issue_date and d180 <= inv.issue_date < d90).mapped('amount')
            )
            growth_rate = 0.0
            if paid_prev_90:
                growth_rate = ((paid_90 - paid_prev_90) / paid_prev_90) * 100.0
            elif paid_90:
                growth_rate = 100.0
            growth_rate = round(growth_rate, 1)

            blocked_modules = len(tenant.module_entitlement_ids.filtered(lambda ent: ent.state == 'blocked'))
            if overdue_count >= 3 or tenant.state != 'active':
                churn_risk = 'critical'
            elif overdue_count >= 1:
                churn_risk = 'medium'
            else:
                churn_risk = 'low'

            if blocked_modules >= 2:
                security_status = 'exposed'
            elif blocked_modules == 1:
                security_status = 'monitoring'
            else:
                security_status = 'secure'

            report_rows.append({
                'tenant_record_id': tenant.id,
                'tenant_id': f"T-{tenant.id:04d}-{(tenant.name or 'T')[0].upper()}",
                'tenant_name': tenant.name,
                'state': tenant.state,
                'package': sub.package_id.name if sub and sub.package_id else '',
                'user_count': len(tenant.user_ids.filtered(lambda u: u.active)),
                'growth_rate': growth_rate,
                'churn_risk': churn_risk,
                'security_status': security_status,
                'overdue_invoices': overdue_count,
                'revenue': round(sum(paid.mapped('amount')), 2),
                'mrr': round(sub.amount if sub and sub.billing_cycle == 'monthly' else (sub.amount / 12.0 if sub else 0.0), 2),
            })

        total = len(report_rows)
        critical = len([row for row in report_rows if row['churn_risk'] == 'critical'])
        active_secure = len([row for row in report_rows if row['state'] == 'active' and row['security_status'] == 'secure'])
        system_integrity = round((active_secure / total) * 100.0, 1) if total else 100.0
        avg_growth = round(sum(row['growth_rate'] for row in report_rows) / total, 1) if total else 0.0
        prediction = max(65.0, min(99.9, round(92.0 + (avg_growth / 12.0) - (critical * 1.5), 1)))
        revenue_stability = max(20.0, min(98.0, round(100.0 - (critical * 12.0), 1)))
        metrics = self._analytics_metric_defs()

        return {
            'generated_at': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'selected_metrics': selected_metrics or [m['key'] for m in metrics[:4]],
            'available_metrics': metrics,
            'summary': {
                'total_tenants': total,
                'active_count': len([row for row in report_rows if row['state'] == 'active']),
                'risk_count': len([row for row in report_rows if row['churn_risk'] != 'low']),
                'system_health': system_integrity,
                'neural_prediction': prediction,
            },
            'risk_heatmap': {
                'system_integrity': system_integrity,
                'revenue_stability': revenue_stability,
            },
            'report_rows': report_rows,
        }

    @http.route('/tcrm_master/analytics', type='jsonrpc', auth='user')
    def get_analytics(self, metrics=None):
        self._check_master_access()
        return self._prepare_advanced_analytics_data(selected_metrics=metrics or [])

    @http.route('/tcrm_master/analytics/advanced', type='jsonrpc', auth='user')
    def get_advanced_analytics(self, metrics=None):
        self._check_master_access()
        return self._prepare_advanced_analytics_data(selected_metrics=metrics or [])

    @http.route('/tcrm_master/tenants/report_data', type='jsonrpc', auth='user')
    def get_tenants_report_data(self, metrics=None):
        self._check_master_access()
        data = self._prepare_advanced_analytics_data(selected_metrics=metrics or [])
        return {
            'report_rows': data['report_rows'],
            'generated_at': data['generated_at'],
            'summary': data['summary'],
        }

    @http.route('/tcrm_master/analytics/export', type='http', auth='user')
    def export_analytics(self, format='csv'):
        self._check_master_access()
        data = self._prepare_advanced_analytics_data()
        rows = data['report_rows']
        filename_base = f"tcrm_analytics_{date.today().isoformat()}"

        if format == 'csv':
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Tenant ID', 'Tenant', 'Growth Rate', 'Churn Risk', 'Security Status', 'Revenue', 'MRR'])
            for row in rows:
                writer.writerow([
                    row['tenant_id'],
                    row['tenant_name'],
                    f"{row['growth_rate']}%",
                    row['churn_risk'],
                    row['security_status'],
                    row['revenue'],
                    row['mrr'],
                ])
            content = output.getvalue()
            return request.make_response(content, headers=[
                ('Content-Type', 'text/csv; charset=utf-8'),
                ('Content-Disposition', f'attachment; filename={filename_base}.csv'),
            ])

        if format in ('excel', 'xlsx'):
            import io
            import xlsxwriter

            output = io.BytesIO()
            wb = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = wb.add_worksheet('Advanced Analytics')
            header_fmt = wb.add_format({'bold': True, 'bg_color': '#132030', 'font_color': '#D6E4F9'})
            pct_fmt = wb.add_format({'num_format': '0.0%'})
            money_fmt = wb.add_format({'num_format': '#,##0.00'})

            headers = ['Tenant ID', 'Tenant', 'Growth Rate', 'Churn Risk', 'Security Status', 'Revenue', 'MRR']
            for col, header in enumerate(headers):
                ws.write(0, col, header, header_fmt)
                ws.set_column(col, col, 18)

            for idx, row in enumerate(rows, start=1):
                ws.write(idx, 0, row['tenant_id'])
                ws.write(idx, 1, row['tenant_name'])
                ws.write_number(idx, 2, (row['growth_rate'] or 0.0) / 100.0, pct_fmt)
                ws.write(idx, 3, row['churn_risk'])
                ws.write(idx, 4, row['security_status'])
                ws.write_number(idx, 5, row['revenue'] or 0.0, money_fmt)
                ws.write_number(idx, 6, row['mrr'] or 0.0, money_fmt)
            wb.close()
            output.seek(0)
            return request.make_response(output.read(), headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename_base}.xlsx'),
            ])

        if format == 'pdf':
            lines = [
                f"{row['tenant_id']} | {row['tenant_name']} | growth {row['growth_rate']}% | risk {row['churn_risk']} | security {row['security_status']}"
                for row in rows
            ]
            pdf_bytes = self._build_simple_pdf(_('TCRM Advanced Analytics Report'), lines)
            return request.make_response(pdf_bytes, headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename={filename_base}.pdf'),
            ])

        return request.not_found()

    # ── Subscription CRUD ──────────────────────────────────────────

    @http.route('/tcrm_master/subscription/create', type='jsonrpc', auth='user')
    def create_subscription(self, tenant_id, package_id, billing_cycle='monthly'):
        self._check_master_access()
        env = self._sudo_env()
        sub = env['tcrm.tenant.subscription'].sudo().create({
            'tenant_id': tenant_id,
            'package_id': package_id,
            'billing_cycle': billing_cycle,
            'status': 'active',
            'start_date': fields.Date.today(),
            'auto_renew': True,
        })
        return {'id': sub.id, 'name': sub.name}

    # ── Domain CRUD ────────────────────────────────────────────────

    @http.route('/tcrm_master/domain/create', type='jsonrpc', auth='user')
    def create_domain(self, tenant_id, domain, is_primary=False):
        self._check_master_access()
        env = self._sudo_env()
        d = env['tcrm.tenant.domain'].sudo().create({
            'tenant_id': tenant_id,
            'domain': domain,
            'is_primary': is_primary,
        })
        return {'id': d.id}

    @http.route('/tcrm_master/domain/delete', type='jsonrpc', auth='user')
    def delete_domain(self, domain_id):
        self._check_master_access()
        env = self._sudo_env()
        d = env['tcrm.tenant.domain'].sudo().browse(domain_id)
        if d.exists():
            d.unlink()
        return {'ok': True}

    # ── Invoice CRUD ───────────────────────────────────────────────

    @http.route('/tcrm_master/invoice/create', type='jsonrpc', auth='user')
    def create_invoice(self, tenant_id, amount, due_date, notes=''):
        self._check_master_access()
        env = self._sudo_env()
        tenant = env['tcrm.tenant'].sudo().browse(tenant_id)
        if not tenant.exists():
            return {'error': _('Tenant not found')}
        sub = tenant.active_subscription_id
        inv = env['tcrm.tenant.invoice'].sudo().create({
            'tenant_id': tenant_id,
            'subscription_id': sub.id if sub else False,
            'amount': amount,
            'currency_id': env.company.currency_id.id,
            'due_date': due_date,
            'state': 'open',
            'notes': notes,
        })
        return {'id': inv.id, 'name': inv.name}

    # ── Packages list ──────────────────────────────────────────────

    @http.route('/tcrm_master/packages', type='jsonrpc', auth='user')
    def get_packages(self):
        self._check_master_access()
        env = self._sudo_env()
        packages = env['tcrm.saas.package'].sudo().search([('active', '=', True)])
        return [{
            'id': p.id,
            'name': p.name,
            'code': p.code,
            'monthly_price': p.monthly_price,
            'yearly_price': p.yearly_price,
            'user_limit': p.user_limit,
            'storage_limit_gb': p.storage_limit_gb,
            'module_count': p.module_count,
            'module_ids': p.module_ids.ids,
            'modules': [{
                'id': m.id,
                'name': m.name,
                'display_name': m.shortdesc or m.name,
                'state': m.state,
            } for m in p.module_ids],
        } for p in packages]

    @http.route('/tcrm_master/apps/catalog', type='jsonrpc', auth='user')
    def get_apps_catalog(self):
        """List all installed official free application modules for super-admin assignment."""
        self._check_master_access()
        env = self._sudo_env()
        # Keep catalog package in sync with installed apps
        env['tcrm.saas.package']._ensure_all_apps_package()
        apps = env['ir.module.module'].sudo().search([
            ('application', '=', True),
            ('state', '=', 'installed'),
        ], order='shortdesc, name')
        return {
            'total': len(apps),
            'apps': [{
                'id': m.id,
                'name': m.name,
                'display_name': m.shortdesc or m.name,
                'summary': m.summary or '',
                'category': m.category_id.display_name if m.category_id else '',
                'author': m.author or '',
                'state': m.state,
                'license': m.license or '',
            } for m in apps],
        }

    @http.route('/tcrm_master/packages/set_modules', type='jsonrpc', auth='user')
    def set_package_modules(self, package_id, module_ids=None, fill_all=False):
        """Assign selected apps (or all free apps) to a SaaS package."""
        if not request.env.user.has_group('base.group_system'):
            return {'error': _('Only System Administrator can edit package apps.')}
        env = self._sudo_env()
        package = env['tcrm.saas.package'].browse(int(package_id))
        if not package.exists():
            return {'error': _('Package not found')}
        if fill_all:
            package.action_fill_all_installed_apps()
        else:
            mods = env['ir.module.module'].browse(module_ids or []).exists()
            mods = mods.filtered(lambda m: m.application and m.state == 'installed')
            package.module_ids = [(6, 0, mods.ids)]
            subs = env['tcrm.tenant.subscription'].search([
                ('package_id', '=', package.id),
                ('status', 'in', ('trial', 'active', 'past_due')),
            ])
            subs.mapped('tenant_id')._sync_module_entitlements_from_subscription()
        return {
            'ok': True,
            'package_id': package.id,
            'module_count': len(package.module_ids),
            'module_ids': package.module_ids.ids,
        }

    @http.route('/tcrm_master/tenant/module/grant', type='jsonrpc', auth='user')
    def grant_tenant_module(self, tenant_id, module_id, state='allowed'):
        """Manually grant/block an app on a tenant profile (super-admin)."""
        if not request.env.user.has_group('base.group_system'):
            return {'error': _('Only System Administrator can grant tenant apps.')}
        env = self._sudo_env()
        tenant = env['tcrm.tenant'].browse(int(tenant_id))
        module = env['ir.module.module'].browse(int(module_id))
        if not tenant.exists():
            return {'error': _('Tenant not found')}
        if not module.exists() or not module.application or module.state != 'installed':
            return {'error': _('Module is not an installed application')}
        if state == 'blocked':
            ent = tenant.action_revoke_module(module)
        else:
            ent = tenant.action_grant_module(module, state=state)
        return {
            'ok': True,
            'entitlement_id': ent.id,
            'state': ent.state,
            'module_name': module.shortdesc or module.name,
        }

    # ── Sectors list ───────────────────────────────────────────────

    @http.route('/tcrm_master/sectors', type='jsonrpc', auth='user')
    def get_sectors(self):
        self._check_master_access()
        env = self._sudo_env()
        sectors = env['tcrm.tenant.sector'].sudo().search([('active', '=', True)])
        return [{'id': s.id, 'name': s.name, 'code': s.code} for s in sectors]

    # ══ GOD-MODE ENDPOINTS ═════════════════════════════════════════

    @http.route('/tcrm_master/tenant/ghost_login', type='jsonrpc', auth='user')
    def ghost_login(self, tenant_id):
        """Return a URL to open the tenant's company context in a new tab."""
        if not request.env.user.has_group('base.group_system'):
            return {'error': _('Ghost Login requires System Administrator privileges.')}
        env = self._sudo_env()
        tenant = env['tcrm.tenant'].browse(int(tenant_id))
        if not tenant.exists():
            return {'error': _('Tenant not found.')}
        company = tenant.company_id
        if not company:
            return {'error': _('Tenant has no linked company.')}
        base_url = env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        if tenant.db_name:
            return {
                'action': 'open_tab',
                'url': f'{base_url}/tcrm?db={tenant.db_name}',
                'label': _('Opening dedicated DB: %s') % tenant.db_name,
            }
        return {
            'action': 'open_tab',
            'url': f'{base_url}/tcrm?cids={company.id}',
            'label': _('Switching to company: %s') % company.name,
        }

    @http.route('/tcrm_master/tenant/freeze', type='jsonrpc', auth='user')
    def freeze_tenant(self, tenant_id, freeze=True):
        """Freeze (deactivate all users) or unfreeze a tenant account."""
        if not request.env.user.has_group('base.group_system'):
            return {'error': _('Freeze requires System Administrator privileges.')}
        env = self._sudo_env()
        tenant = env['tcrm.tenant'].browse(int(tenant_id))
        if not tenant.exists():
            return {'error': _('Tenant not found.')}
        if freeze:
            tenant.action_freeze_tenant()
            return {'status': 'frozen', 'is_frozen': True,
                    'message': _('Tenant "%s" frozen — all user sessions revoked.') % tenant.name}
        else:
            tenant.action_unfreeze_tenant()
            return {'status': 'unfrozen', 'is_frozen': False,
                    'message': _('Tenant "%s" unfrozen — users reactivated.') % tenant.name}

    @http.route('/tcrm_master/tenant/update_pin', type='jsonrpc', auth='user')
    def update_tenant_pin(self, tenant_id, latitude=0.0, longitude=0.0, google_maps_link=''):
        """Update a tenant's map pin. Accepts raw lat/lon or a Google Maps link."""
        self._check_master_access()
        env = self._sudo_env()
        tenant = env['tcrm.tenant'].browse(int(tenant_id))
        if not tenant.exists():
            return {'error': _('Tenant not found.')}
        lat = float(latitude or 0)
        lon = float(longitude or 0)
        link = (google_maps_link or '').strip()
        if link:
            coords = tenant._parse_google_maps_link(link)
            if coords:
                lat, lon = coords
        vals = {'latitude': lat, 'longitude': lon}
        if link:
            vals['google_maps_link'] = link
        tenant.write(vals)
        return {'ok': True, 'lat': tenant.latitude, 'lon': tenant.longitude}

    @http.route('/tcrm_master/global/employees', type='jsonrpc', auth='user')
    def get_global_employees(self, search='', tenant_id=None):
        """Global employee list across all tenants with tenant attribution."""
        self._check_master_access()
        env = self._sudo_env()
        Tenant = env['tcrm.tenant'].sudo()
        User = env['res.users'].sudo()

        tenants = Tenant.search([])
        company_to_tenant = {t.company_id.id: t for t in tenants if t.company_id}

        domain = [('active', '=', True), ('share', '=', False)]
        if tenant_id:
            t = Tenant.browse(int(tenant_id))
            if t.exists() and t.company_id:
                domain.append(('company_id', '=', t.company_id.id))
        if search:
            domain += ['|', ('name', 'ilike', search), ('login', 'ilike', search)]

        users = User.search(domain, order='name', limit=200)
        uids = users.ids
        groups_map = self._group_labels_for_user_ids(env, uids)
        result = []
        for u in users:
            tenant_rec = company_to_tenant.get(u.company_id.id)
            result.append({
                'id': u.id,
                'name': u.name,
                'login': u.login,
                'company': u.company_id.name if u.company_id else '',
                'company_id': u.company_id.id if u.company_id else 0,
                'tenant_id': tenant_rec.id if tenant_rec else 0,
                'tenant_name': tenant_rec.name if tenant_rec else _('Master'),
                'groups': groups_map.get(u.id, [])[:3],
                'active': u.active,
                'last_login': str(u.login_date) if u.login_date else '',
                'is_master_admin': u.has_group('base.group_system'),
            })
        return result

    @http.route('/tcrm_master/user/roles', type='jsonrpc', auth='user')
    def list_user_roles(self):
        """Return GOD-mode tenant role catalog for the Change Role UI."""
        self._check_master_access()
        env = self._sudo_env()
        roles = []
        for key, xmlid, label, help_text in self.TENANT_ROLE_CATALOG:
            group = env.ref(xmlid, raise_if_not_found=False)
            if group:
                roles.append({
                    'key': key,
                    'xmlid': xmlid,
                    'label': label,
                    'help': help_text,
                    'group_id': group.id,
                })
        return {'roles': roles}

    @http.route('/tcrm_master/user/reset_password', type='jsonrpc', auth='user')
    def reset_user_password(self, user_id, new_password):
        """Force-set a user's password (system admin only)."""
        if not request.env.user.has_group('base.group_system'):
            return {'error': _('Password reset requires System Administrator privileges.')}
        if not new_password or len(new_password) < 6:
            return {'error': _('New password must be at least 6 characters.')}
        env = self._sudo_env()
        user = env['res.users'].browse(int(user_id))
        if not user.exists():
            return {'error': _('User not found.')}
        user.write({'password': new_password})
        return {'ok': True, 'message': _('Password updated for %s.') % user.name}

    @http.route('/tcrm_master/user/change_role', type='jsonrpc', auth='user')
    def change_user_role(self, user_id, role):
        """Assign a tenant GOD-mode role (replaces other TCRM tenant roles)."""
        if not request.env.user.has_group('base.group_system'):
            return {'error': _('Role change requires System Administrator privileges.')}
        env = self._sudo_env()
        user = env['res.users'].browse(int(user_id))
        if not user.exists():
            return {'error': _('User not found.')}

        role_map = {key: xmlid for key, xmlid, _label, _help in self.TENANT_ROLE_CATALOG}
        if role not in role_map:
            return {'error': _('Invalid role. Choose one of: %s') % ', '.join(role_map)}

        target = env.ref(role_map[role], raise_if_not_found=False)
        if not target:
            return {'error': _('Role group not found. Upgrade tcrm_saas_core and retry.')}

        tcrm_role_ids = set()
        for _key, xmlid, _label, _help in self.TENANT_ROLE_CATALOG:
            g = env.ref(xmlid, raise_if_not_found=False)
            if g:
                tcrm_role_ids.add(g.id)

        keep = user.group_ids.filtered(lambda g: g.id not in tcrm_role_ids)
        user.write({'group_ids': [(6, 0, keep.ids + [target.id])]})
        label = next((lbl for k, _x, lbl, _h in self.TENANT_ROLE_CATALOG if k == role), role)
        return {
            'ok': True,
            'role': role,
            'label': label,
            'message': _('Role updated to %s for %s.') % (label, user.name),
        }

    @http.route('/tcrm_master/ai_health', type='jsonrpc', auth='user')
    def get_ai_health(self):
        """Return health status of all configured AI providers."""
        self._check_master_access()
        env = self._sudo_env()
        providers = []
        try:
            Provider = env['tcrm.ai.provider'].sudo()
            for p in Provider.search([('active', '=', True)]):
                keys = p.key_ids.filtered(lambda k: k.active)
                key_statuses = []
                for k in keys:
                    key_statuses.append({
                        'name': k.name or k.api_key[:8] + '…',
                        'status': k.status if hasattr(k, 'status') else 'active',
                        'last_used': str(k.last_used) if hasattr(k, 'last_used') and k.last_used else '',
                    })
                providers.append({
                    'id': p.id,
                    'name': p.name,
                    'provider_code': p.provider_code,
                    'active': p.active,
                    'default_model': p.default_model or '',
                    'key_count': len(keys),
                    'key_statuses': key_statuses,
                    'health': 'ok' if keys else 'no_keys',
                })
        except Exception as e:
            _logger.warning('AI health check failed: %s', e)
        return {'providers': providers, 'total': len(providers)}
