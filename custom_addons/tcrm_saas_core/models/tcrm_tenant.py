from tcrm import models, fields, api, _
from tcrm.exceptions import UserError, ValidationError
import tcrm.service.db
import logging

_logger = logging.getLogger(__name__)


class TcRmTenant(models.Model):
    _name = 'tcrm.tenant'
    _description = 'TCRM Tenant'

    name = fields.Char(string='Tenant Name', required=True)
    client_name = fields.Char(string='Client Name')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='cascade', index=True)
    sector_id = fields.Many2one('tcrm.tenant.sector', string='Sector')
    support_email = fields.Char(string='Support Email')
    support_phone = fields.Char(string='Support Phone')
    user_ids = fields.One2many('res.users', 'company_id', string='Users')
    domain_ids = fields.One2many('tcrm.tenant.domain', 'tenant_id', string='Domains')
    subscription_ids = fields.One2many('tcrm.tenant.subscription', 'tenant_id', string='Subscriptions')
    module_entitlement_ids = fields.One2many('tcrm.tenant.module.entitlement', 'tenant_id', string='Module Entitlements')
    invoice_ids = fields.One2many('tcrm.tenant.invoice', 'tenant_id', string='Billing Invoices')
    active_subscription_id = fields.Many2one(
        'tcrm.tenant.subscription',
        string='Active Subscription',
        compute='_compute_active_subscription_id',
        store=False,
    )
    primary_domain = fields.Char(string='Primary Domain', compute='_compute_primary_domain', store=False)
    db_name = fields.Char(
        string='Tenant Database',
        help='Optional dedicated tenant database name. Leave empty for single-database multi-company mode.',
    )
    active = fields.Boolean(default=True)
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active')], default='draft')
    is_frozen = fields.Boolean(string='Account Frozen', default=False)
    google_maps_link = fields.Char(string='Google Maps Link', help='Paste a Google Maps share link — coordinates are extracted automatically')
    latitude = fields.Float(string='Latitude', digits=(10, 7))
    longitude = fields.Float(string='Longitude', digits=(10, 7))

    @api.depends('subscription_ids.status')
    def _compute_active_subscription_id(self):
        for rec in self:
            rec.active_subscription_id = rec.subscription_ids.filtered(
                lambda s: s.status in ('trial', 'active', 'past_due')
            )[:1]

    @api.depends('domain_ids.is_primary', 'domain_ids.active', 'domain_ids.domain')
    def _compute_primary_domain(self):
        for rec in self:
            primary = rec.domain_ids.filtered(lambda d: d.is_primary and d.active)[:1]
            rec.primary_domain = primary.domain or False

    @api.constrains('db_name', 'company_id')
    def _check_tenant_constraints(self):
        for rec in self:
            if rec.db_name and (' ' in rec.db_name or '-' in rec.db_name):
                raise ValidationError(_("Database name cannot contain spaces or hyphens."))
            if rec.db_name:
                dup_db = self.search_count([('id', '!=', rec.id), ('db_name', '=', rec.db_name)])
                if dup_db:
                    raise ValidationError(_("Tenant database name must be unique."))
            # Only one *active* tenant per company (archived historical rows are allowed).
            dup_company = self.search_count([
                ('id', '!=', rec.id),
                ('company_id', '=', rec.company_id.id),
                ('active', '=', True),
            ])
            if dup_company and rec.active:
                raise ValidationError(_("Each company can be linked to only one tenant record."))

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = []
        for vals in vals_list:
            values = dict(vals)
            if not values.get('company_id'):
                company_name = values.get('client_name') or values.get('name')
                company_vals = {'name': company_name}
                try_cur = self.env['res.currency'].sudo().with_context(
                    active_test=False
                ).search([('name', '=', 'TRY')], limit=1)
                if try_cur:
                    if not try_cur.active:
                        try_cur.active = True
                    company_vals['currency_id'] = try_cur.id
                country_tr = self.env.ref('base.tr', raise_if_not_found=False)
                if country_tr:
                    company_vals['country_id'] = country_tr.id
                company = self.env['res.company'].create(company_vals)
                values['company_id'] = company.id
            prepared_vals_list.append(values)

        records = super(TcRmTenant, self).create(prepared_vals_list)
        for record, values in zip(records, prepared_vals_list):
            if values.get('db_name'):
                record._create_tenant_db(values['db_name'])
        return records

    def _create_tenant_db(self, db_name):
        if tcrm.service.db.exp_db_exist(db_name):
            _logger.warning("Database %s already exists.", db_name)
            return
        try:
            _logger.info("Creating database %s...", db_name)
            tcrm.service.db.exp_create_database(db_name, demo=False, lang='en_US')
            _logger.info("Database %s created successfully.", db_name)
        except Exception as e:
            _logger.exception("Failed to create database %s", db_name)
            raise UserError(
                _("Failed to create tenant database '%s'. Check PostgreSQL is running and credentials in tcrm.conf. Details: %s")
                % (db_name, str(e))
            ) from e

    @api.model
    def _upsert_tenant_user(self, company, login, name, password, groups):
        user = self.env['res.users'].sudo().search([('login', '=', login)], limit=1)
        vals = {
            'name': name,
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
            'group_ids': [(6, 0, groups.ids)],
            'new_password': password,
            'active': True,
        }
        if user:
            user.write(vals)
            return user
        vals['login'] = login
        return self.env['res.users'].sudo().create(vals)

    @api.model
    def _seed_propertio_sample_data(self, company, admin_user, code):
        project_name = f"{company.name} Main Project"
        project = self.env['propertio.project'].sudo().search(
            [('name', '=', project_name), ('company_id', '=', company.id)], limit=1
        )
        if not project:
            project = self.env['propertio.project'].sudo().create({
                'name': project_name,
                'city': 'Istanbul',
                'company_id': company.id,
            })

        unit_name = f"{code}-A1"
        unit = self.env['propertio.unit'].sudo().search(
            [('name', '=', unit_name), ('project_id', '=', project.id)], limit=1
        )
        if not unit:
            unit = self.env['propertio.unit'].sudo().create({
                'name': unit_name,
                'project_id': project.id,
                'list_price': 4500000.0,
                'state': 'available',
            })

        customer = self.env['res.partner'].sudo().search(
            [('name', '=', f'{company.name} Customer 1'), ('company_id', '=', company.id)], limit=1
        )
        if not customer:
            customer = self.env['res.partner'].sudo().create({
                'name': f'{company.name} Customer 1',
                'email': f'customer1@{code.lower()}.example.com',
                'phone': '+905551112233',
                'company_id': company.id,
            })

        sale = self.env['propertio.sale'].sudo().search(
            [('partner_id', '=', customer.id), ('unit_id', '=', unit.id)], limit=1
        )
        if not sale:
            sale = self.env['propertio.sale'].sudo().create({
                'partner_id': customer.id,
                'unit_id': unit.id,
                'sale_price': 4300000.0,
                'currency_id': company.currency_id.id,
                'date_sale': fields.Date.today(),
            })
            sale.action_confirm()

    @api.model
    def seed_master_demo_data(self):
        # Master-only. Never run while installing modules into a tenant DB.
        if self.env.cr.dbname != 'tcrm_master':
            return True
        # Coherent multi-tenant scenario aligned with the Nova Estates mock data.
        # Coordinates are real Turkish city pins so the Command Center map is editable
        # and useful out of the box (no "estimated" hash pins).
        tenant_specs = [
            {
                'name': 'Test Agency',
                'code': 'test_agency',
                'admin_login': 'agency_admin',
                'sales_login': 'agency_sales',
                'city': 'Ankara',
                'latitude': 39.9208,
                'longitude': 32.8541,
                'maps_link': 'https://www.google.com/maps/@39.9208,32.8541,14z',
                'phone': '+90 312 555 0101',
            },
            {
                'name': 'Blue Horizon Realty',
                'code': 'blue_horizon',
                'admin_login': 'bh_admin',
                'sales_login': 'bh_sales',
                'city': 'Izmir',
                'latitude': 38.4237,
                'longitude': 27.1428,
                'maps_link': 'https://www.google.com/maps/@38.4237,27.1428,14z',
                'phone': '+90 232 555 0202',
            },
            {
                'name': 'Nova Estates',
                'code': 'nova_estates',
                'admin_login': 'nova_admin',
                'sales_login': 'nova_sales',
                'city': 'Istanbul',
                'latitude': 41.0082,
                'longitude': 28.9784,
                'maps_link': 'https://www.google.com/maps/@41.0082,28.9784,14z',
                'phone': '+90 212 555 0303',
            },
        ]
        known_names = {s['name'] for s in tenant_specs}
        mock_data_installed = bool(self.env['ir.module.module'].sudo().search([
            ('name', '=', 'tcrm_mock_data'), ('state', '=', 'installed'),
        ], limit=1))

        tenant_admin_group = self.env.ref('tcrm_saas_core.group_tcrm_tenant_admin')
        tenant_sales_group = self.env.ref('tcrm_saas_core.group_tcrm_tenant_sales')
        base_user_group = self.env.ref('base.group_user')
        partner_manager_group = self.env.ref('base.group_partner_manager')
        sale_model = self.env['ir.model']._get('propertio.sale')
        payment_model = self.env['ir.model']._get('propertio.payment')
        sale_price_field = self.env['ir.model.fields'].search(
            [('model', '=', 'propertio.sale'), ('name', '=', 'sale_price')], limit=1
        )
        payment_amount_field = self.env['ir.model.fields'].search(
            [('model', '=', 'propertio.payment'), ('name', '=', 'amount')], limit=1
        )
        default_sector = self.env.ref('tcrm_saas_core.sector_real_estate', raise_if_not_found=False)
        default_package = self.env.ref('tcrm_saas_core.package_growth', raise_if_not_found=False)

        # Archive extra rows that share a demo brand name (keep newest per name).
        for brand in known_names:
            dupes = self.sudo().with_context(active_test=False).search(
                [('name', '=', brand)], order='id desc'
            )
            if len(dupes) > 1:
                dupes[1:].write({'active': False, 'state': 'draft'})
        self.env.flush_all()

        for spec in tenant_specs:
            name = spec['name']
            code = spec['code']
            admin_login = spec['admin_login']
            sales_login = spec['sales_login']

            # Prefer an existing company with this brand name; create one if missing.
            # Keep each tenant on its own company (SaaS isolation). Nova Estates is
            # still the brand twin of the shared mock-data scenario (same city/pins
            # and inventory naming), without stealing the main company_id.
            company = self.env['res.company'].sudo().search([('name', '=', name)], limit=1)
            if not company:
                company = self.env['res.company'].sudo().create({'name': name})

            # One active tenant per company. Prefer the row already branded with this
            # name, otherwise the newest row; archive every other row for the company.
            company_tenants = self.sudo().with_context(active_test=False).search(
                [('company_id', '=', company.id)], order='id desc'
            )
            tenant = company_tenants.filtered(lambda t: t.name == name)[:1] or company_tenants[:1]
            others = company_tenants - tenant
            if others:
                others.write({'active': False, 'state': 'draft'})
                self.env.flush_all()

            client_name = f"{name} — {spec['city']}"
            if code == 'nova_estates' and mock_data_installed:
                client_name = f"{name} — {spec['city']} (linked to shared mock-data scenario)"

            vals = {
                'name': name,
                'client_name': client_name,
                'company_id': company.id,
                'sector_id': default_sector.id if default_sector else False,
                'support_email': f'support@{code}.example.com',
                'support_phone': spec['phone'],
                'db_name': False,
                'active': True,
                'state': 'active',
                'latitude': spec['latitude'],
                'longitude': spec['longitude'],
                'google_maps_link': spec['maps_link'],
                'is_frozen': False,
            }
            if tenant:
                tenant.write(vals)
            else:
                # Guard against races / leftover actives before create.
                self.sudo().with_context(active_test=False).search([
                    ('company_id', '=', company.id), ('active', '=', True),
                ]).write({'active': False, 'state': 'draft'})
                self.env.flush_all()
                tenant = self.sudo().create(vals)

            admin_user = self._upsert_tenant_user(
                company=company,
                login=admin_login,
                name=f'{name} Admin',
                password='Admin#2026',
                groups=tenant_admin_group | base_user_group | partner_manager_group,
            )
            sales_user = self._upsert_tenant_user(
                company=company,
                login=sales_login,
                name=f'{name} Sales',
                password='Sales#2026',
                groups=tenant_sales_group | base_user_group,
            )

            permission_set = self.env['tcrm.permission.set'].sudo().search(
                [('name', '=', _('Sales Financial Read-Only')), ('company_id', '=', company.id)],
                limit=1,
            )
            if not permission_set:
                permission_set = self.env['tcrm.permission.set'].sudo().create({
                    'name': _('Sales Financial Read-Only'),
                    'company_id': company.id,
                    'active': True,
                })
            if sale_model and sale_price_field:
                line = self.env['tcrm.permission.set.line'].sudo().search(
                    [
                        ('permission_set_id', '=', permission_set.id),
                        ('field_id', '=', sale_price_field.id),
                    ],
                    limit=1,
                )
                if not line:
                    self.env['tcrm.permission.set.line'].sudo().create({
                        'permission_set_id': permission_set.id,
                        'model_id': sale_model.id,
                        'field_id': sale_price_field.id,
                        'can_read': True,
                        'can_write': False,
                    })
            if payment_model and payment_amount_field:
                line = self.env['tcrm.permission.set.line'].sudo().search(
                    [
                        ('permission_set_id', '=', permission_set.id),
                        ('field_id', '=', payment_amount_field.id),
                    ],
                    limit=1,
                )
                if not line:
                    self.env['tcrm.permission.set.line'].sudo().create({
                        'permission_set_id': permission_set.id,
                        'model_id': payment_model.id,
                        'field_id': payment_amount_field.id,
                        'can_read': True,
                        'can_write': False,
                    })
            sales_user.sudo().write({'permission_set_ids': [(6, 0, [permission_set.id])]})
            self._seed_propertio_sample_data(company, admin_user, code)

            if default_package:
                sub = self.env['tcrm.tenant.subscription'].sudo().search(
                    [('tenant_id', '=', tenant.id), ('status', 'in', ['trial', 'active', 'past_due'])],
                    limit=1,
                )
                if not sub:
                    self.env['tcrm.tenant.subscription'].sudo().create(
                        {
                            'tenant_id': tenant.id,
                            'package_id': default_package.id,
                            'billing_cycle': 'monthly',
                            'status': 'active',
                            'start_date': fields.Date.today(),
                            'auto_renew': True,
                        }
                    )
                tenant._sync_module_entitlements_from_subscription()

            domain_name = f'{code}.tcrm.local'
            domain = self.env['tcrm.tenant.domain'].sudo().search([('domain', '=', domain_name)], limit=1)
            if not domain:
                self.env['tcrm.tenant.domain'].sudo().create(
                    {
                        'tenant_id': tenant.id,
                        'domain': domain_name,
                        'is_primary': True,
                        'verified': True,
                        'ssl_status': 'active',
                        'active': True,
                    }
                )

        _logger.info("TCRM SaaS Core demo seed data loaded.")
        return True

    # ── God-Mode: Location ───────────────────────────────────────────

    @api.onchange('google_maps_link')
    def _onchange_google_maps_link(self):
        if self.google_maps_link:
            coords = self._parse_google_maps_link(self.google_maps_link)
            if coords:
                self.latitude, self.longitude = coords

    @api.model
    def _parse_google_maps_link(self, link):
        import re
        patterns = [
            r'@(-?\d+\.?\d*),(-?\d+\.?\d*)',           # @lat,lon
            r'[?&]ll=(-?\d+\.?\d*),(-?\d+\.?\d*)',      # ll=lat,lon
            r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)',        # !3dlat!4dlon
            r'/(-?\d{2,3}\.\d{4,}),(-?\d{1,3}\.\d{4,})', # /lat,lon path
        ]
        for pat in patterns:
            m = re.search(pat, link)
            if m:
                return float(m.group(1)), float(m.group(2))
        return None

    # ── God-Mode: Freeze / Unfreeze ──────────────────────────────────

    def action_freeze_tenant(self):
        for tenant in self:
            if not tenant.company_id:
                continue
            root = self.env.ref('base.user_root', raise_if_not_found=False)
            admin = self.env.ref('base.user_admin', raise_if_not_found=False)
            exclude = [u.id for u in [root, admin] if u]
            users = self.env['res.users'].sudo().search([
                ('company_id', '=', tenant.company_id.id),
                ('id', 'not in', exclude),
            ])
            users.write({'active': False})
            tenant.is_frozen = True
        return True

    def action_unfreeze_tenant(self):
        for tenant in self:
            if not tenant.company_id:
                continue
            root = self.env.ref('base.user_root', raise_if_not_found=False)
            admin = self.env.ref('base.user_admin', raise_if_not_found=False)
            exclude = [u.id for u in [root, admin] if u]
            users = self.env['res.users'].sudo().with_context(active_test=False).search([
                ('company_id', '=', tenant.company_id.id),
                ('id', 'not in', exclude),
            ])
            users.write({'active': True})
            tenant.is_frozen = False
        return True

    def action_grant_module(self, module, state='allowed', note=False):
        """Manually grant a module entitlement to this tenant (super-admin)."""
        self.ensure_one()
        Ent = self.env['tcrm.tenant.module.entitlement'].sudo()
        existing = Ent.search([
            ('tenant_id', '=', self.id),
            ('module_id', '=', module.id),
        ], limit=1)
        if existing:
            existing.write({'state': state, 'source': 'manual', 'note': note or existing.note})
            return existing
        return Ent.create({
            'tenant_id': self.id,
            'module_id': module.id,
            'state': state,
            'source': 'manual',
            'note': note or False,
        })

    def action_revoke_module(self, module):
        """Block a module for this tenant (keeps the entitlement row for audit)."""
        self.ensure_one()
        Ent = self.env['tcrm.tenant.module.entitlement'].sudo()
        existing = Ent.search([
            ('tenant_id', '=', self.id),
            ('module_id', '=', module.id),
        ], limit=1)
        if existing:
            existing.write({'state': 'blocked', 'source': 'manual'})
            return existing
        return Ent.create({
            'tenant_id': self.id,
            'module_id': module.id,
            'state': 'blocked',
            'source': 'manual',
        })

    def _sync_module_entitlements_from_subscription(self):
        for tenant in self:
            subscription = tenant.subscription_ids.filtered(lambda s: s.status in ('trial', 'active', 'past_due'))[:1]
            if not subscription:
                continue
            package_modules = subscription.package_id.module_ids
            existing = self.env['tcrm.tenant.module.entitlement'].search([('tenant_id', '=', tenant.id)])
            existing_by_module = {e.module_id.id: e for e in existing}

            for module in package_modules:
                if module.id in existing_by_module:
                    if existing_by_module[module.id].source == 'package':
                        existing_by_module[module.id].state = 'allowed'
                    continue
                self.env['tcrm.tenant.module.entitlement'].create({
                    'tenant_id': tenant.id,
                    'module_id': module.id,
                    'state': 'allowed',
                    'source': 'package',
                })

            package_module_ids = set(package_modules.ids)
            for entitlement in existing.filtered(lambda e: e.source == 'package' and e.module_id.id not in package_module_ids):
                entitlement.state = 'blocked'

    def _sync_entitlements_from_module_names(self, module_names, source='provision', state='allowed'):
        """Create/allow entitlements from a technical module name list (e.g. provision job)."""
        Module = self.env['ir.module.module'].sudo()
        Ent = self.env['tcrm.tenant.module.entitlement'].sudo()
        names = [n.strip() for n in (module_names or []) if n and str(n).strip()]
        # Skip pure framework modules that clutter Access Management.
        skip = {'base', 'web', 'mail'}
        names = [n for n in names if n not in skip]
        if not names:
            return Ent
        modules = Module.search([('name', 'in', names)])
        created = Ent
        for tenant in self:
            for module in modules:
                existing = Ent.search([
                    ('tenant_id', '=', tenant.id),
                    ('module_id', '=', module.id),
                ], limit=1)
                if existing:
                    # Never override a manual block with provision sync.
                    if existing.source == 'manual' and existing.state == 'blocked':
                        continue
                    if existing.state != state or existing.source == 'package':
                        vals = {'state': state}
                        if existing.source != 'manual':
                            vals['source'] = source
                        existing.write(vals)
                    created |= existing
                else:
                    created |= Ent.create({
                        'tenant_id': tenant.id,
                        'module_id': module.id,
                        'state': state,
                        'source': source,
                    })
        return created

    def _ensure_default_subscription(self, package_code='growth'):
        """Ensure tenant has an active subscription so Access Management can sync apps."""
        Package = self.env['tcrm.saas.package'].sudo()
        Package._ensure_default_package_modules()
        Sub = self.env['tcrm.tenant.subscription'].sudo()
        for tenant in self:
            if tenant.subscription_ids.filtered(lambda s: s.status in ('trial', 'active', 'past_due')):
                continue
            pkg = Package.search([('code', '=', package_code), ('active', '=', True)], limit=1)
            if not pkg:
                pkg = Package.search([('code', '=', 'all_free_apps')], limit=1)
            if not pkg:
                pkg = Package.search([('active', '=', True)], limit=1)
            if not pkg:
                continue
            Sub.create({
                'tenant_id': tenant.id,
                'package_id': pkg.id,
                'billing_cycle': 'monthly',
                'status': 'trial',
            })
            tenant._sync_module_entitlements_from_subscription()
        return True

    def action_sync_entitlements_from_provision(self):
        """Backfill Access Management rows from the latest provisioning module_set."""
        Job = self.env['tcrm.provisioning.job'].sudo() if 'tcrm.provisioning.job' in self.env else None
        for tenant in self:
            names = []
            if Job is not None:
                job = Job.search([('tenant_id', '=', tenant.id)], order='id desc', limit=1)
                if job and job.module_set:
                    names = [n.strip() for n in job.module_set.split(',') if n.strip()]
            if not names:
                # Fallback: product defaults used for dedicated tenants.
                names = [
                    'crm', 'contacts', 'tcrm_propertio', 'tcrm_call_center', 'tcrm_web_enhance',
                ]
            tenant._ensure_default_subscription('growth')
            tenant._sync_entitlements_from_module_names(names, source='provision')
        return True
