import re

from dateutil.relativedelta import relativedelta

from tcrm import api, fields, models, _
from tcrm.exceptions import ValidationError


class TcrmTenantSector(models.Model):
    _name = "tcrm.tenant.sector"
    _description = "Tenant Sector"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    notes = fields.Text(translate=True)

    _sql_constraints = [
        ("tcrm_tenant_sector_code_uniq", "unique(code)", "Sector code must be unique."),
    ]


class TcrmSaasPackage(models.Model):
    _name = "tcrm.saas.package"
    _description = "SaaS Package"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    currency_id = fields.Many2one("res.currency", required=True, default=lambda self: self.env.company.currency_id.id)
    monthly_price = fields.Monetary(currency_field="currency_id", default=0.0)
    yearly_price = fields.Monetary(currency_field="currency_id", default=0.0)
    user_limit = fields.Integer(default=5)
    storage_limit_gb = fields.Integer(default=10)
    module_ids = fields.Many2many(
        "ir.module.module",
        "tcrm_package_module_rel",
        "package_id",
        "module_id",
        string="Allowed Modules",
        domain=[("application", "=", True), ("state", "=", "installed")],
        help="Official free apps (and other installed applications) that tenants on this package may use.",
    )
    module_count = fields.Integer(compute="_compute_module_count")
    feature_line_ids = fields.One2many("tcrm.saas.package.feature", "package_id", string="Features")

    _sql_constraints = [
        ("tcrm_saas_package_code_uniq", "unique(code)", "Package code must be unique."),
    ]

    @api.depends("module_ids")
    def _compute_module_count(self):
        for rec in self:
            rec.module_count = len(rec.module_ids)

    def action_fill_all_installed_apps(self):
        """Super-admin helper: put every installed application module on this package."""
        self.ensure_one()
        apps = self._installed_application_modules()
        self.module_ids = [(6, 0, apps.ids)]
        # Re-sync entitlements for tenants on this package
        subs = self.env["tcrm.tenant.subscription"].sudo().search([
            ("package_id", "=", self.id),
            ("status", "in", ("trial", "active", "past_due")),
        ])
        subs.mapped("tenant_id")._sync_module_entitlements_from_subscription()
        return True

    @api.model
    def _installed_application_modules(self):
        return self.env["ir.module.module"].sudo().search([
            ("application", "=", True),
            ("state", "=", "installed"),
        ], order="shortdesc, name")

    @api.model
    def _modules_by_technical_names(self, names):
        """Resolve ir.module.module rows by technical name (application or not)."""
        names = [n for n in (names or []) if n]
        if not names:
            return self.env["ir.module.module"]
        return self.env["ir.module.module"].sudo().search([("name", "in", names)])

    @api.model
    def _ensure_default_package_modules(self):
        """Ensure Starter/Growth packages reference real installed modules by name.

        XML refs like base.module_tcrm_* can be empty after noupdate installs;
        resolve by technical name instead so Access Management is never stuck
        with a package that grants nothing useful.
        """
        Package = self.sudo()
        defaults = {
            "starter": ["crm", "tcrm_propertio", "contacts"],
            "growth": [
                "crm", "tcrm_propertio", "tcrm_call_center", "tcrm_web_enhance",
                "contacts", "calendar", "project_todo", "account",
            ],
        }
        for code, names in defaults.items():
            pkg = Package.search([("code", "=", code)], limit=1)
            if not pkg:
                continue
            mods = self._modules_by_technical_names(names)
            # Prefer application modules when present; keep non-apps that matter for product.
            apps = mods.filtered(lambda m: m.application and m.state == "installed")
            extras = mods.filtered(lambda m: not m.application and m.state == "installed")
            target = apps | extras
            if target and (not pkg.module_ids or set(pkg.module_ids.ids) != set(target.ids)):
                # Only auto-fill when package is empty or missing key product apps.
                if not pkg.module_ids or not (pkg.module_ids & apps):
                    pkg.module_ids = [(6, 0, target.ids)]
        return True

    @api.model
    def _ensure_all_apps_package(self):
        """Create/update the master 'All Free Apps' package for super-admin assignment."""
        self._ensure_default_package_modules()
        Package = self.sudo()
        pkg = Package.search([("code", "=", "all_free_apps")], limit=1)
        apps = self._installed_application_modules()
        vals = {
            "name": "All Free Apps",
            "code": "all_free_apps",
            "sequence": 100,
            "description": "Catalog of every installed official free application. "
                           "Assign selected apps to tenant packages as needed.",
            "monthly_price": 0.0,
            "yearly_price": 0.0,
            "user_limit": 0,
            "storage_limit_gb": 0,
            "module_ids": [(6, 0, apps.ids)],
            "active": True,
        }
        if pkg:
            pkg.write(vals)
        else:
            pkg = Package.create(vals)
        return pkg


class TcrmSaasPackageFeature(models.Model):
    _name = "tcrm.saas.package.feature"
    _description = "SaaS Package Feature"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    package_id = fields.Many2one("tcrm.saas.package", required=True, ondelete="cascade")
    name = fields.Char(required=True, translate=True)
    value = fields.Char(translate=True)


class TcrmTenantSubscription(models.Model):
    _name = "tcrm.tenant.subscription"
    _description = "Tenant Subscription"
    _order = "id desc"

    name = fields.Char(compute="_compute_name", store=True)
    tenant_id = fields.Many2one("tcrm.tenant", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="tenant_id.company_id", store=True, readonly=True)
    package_id = fields.Many2one("tcrm.saas.package", required=True)
    billing_cycle = fields.Selection([("monthly", "Monthly"), ("yearly", "Yearly")], default="monthly", required=True)
    status = fields.Selection(
        [
            ("trial", "Trial"),
            ("active", "Active"),
            ("past_due", "Past Due"),
            ("suspended", "Suspended"),
            ("cancelled", "Cancelled"),
        ],
        default="trial",
        required=True,
    )
    start_date = fields.Date(required=True, default=fields.Date.today)
    end_date = fields.Date()
    next_invoice_date = fields.Date()
    auto_renew = fields.Boolean(default=True)
    amount = fields.Monetary(currency_field="currency_id", compute="_compute_amount", store=True)
    currency_id = fields.Many2one(related="package_id.currency_id", store=True, readonly=True)
    notes = fields.Text(translate=True)
    invoice_ids = fields.One2many("tcrm.tenant.invoice", "subscription_id", string="Invoices")

    @api.depends("tenant_id", "package_id", "billing_cycle")
    def _compute_name(self):
        for rec in self:
            tenant = rec.tenant_id.display_name if rec.tenant_id else ""
            package = rec.package_id.display_name if rec.package_id else ""
            cycle = dict(self._fields["billing_cycle"].selection).get(rec.billing_cycle, "")
            rec.name = f"{tenant} - {package} ({cycle})" if tenant and package else tenant or package

    @api.depends("package_id", "billing_cycle")
    def _compute_amount(self):
        for rec in self:
            if rec.billing_cycle == "yearly":
                rec.amount = rec.package_id.yearly_price
            else:
                rec.amount = rec.package_id.monthly_price

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._sync_next_invoice_date()
            rec.tenant_id._sync_module_entitlements_from_subscription()
        return records

    def write(self, vals):
        res = super().write(vals)
        if {"start_date", "billing_cycle", "status", "auto_renew"} & set(vals.keys()):
            for rec in self:
                rec._sync_next_invoice_date()
        if "package_id" in vals:
            self.mapped("tenant_id")._sync_module_entitlements_from_subscription()
        return res

    def _sync_next_invoice_date(self):
        for rec in self:
            if rec.status in ("cancelled", "suspended"):
                rec.next_invoice_date = False
                continue
            base = rec.start_date or fields.Date.today()
            rec.next_invoice_date = base if not rec.next_invoice_date else rec.next_invoice_date
            if rec.next_invoice_date and rec.next_invoice_date < fields.Date.today():
                step = relativedelta(months=1) if rec.billing_cycle == "monthly" else relativedelta(years=1)
                next_date = rec.next_invoice_date
                today = fields.Date.today()
                while next_date < today:
                    next_date = next_date + step
                rec.next_invoice_date = next_date


class TcrmTenantDomain(models.Model):
    _name = "tcrm.tenant.domain"
    _description = "Tenant Domain"
    _order = "id desc"

    tenant_id = fields.Many2one("tcrm.tenant", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="tenant_id.company_id", store=True, readonly=True)
    domain = fields.Char(required=True)
    is_primary = fields.Boolean(default=False)
    verified = fields.Boolean(default=False)
    ssl_status = fields.Selection(
        [("pending", "Pending"), ("active", "Active"), ("failed", "Failed")],
        default="pending",
        required=True,
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("tcrm_tenant_domain_uniq", "unique(domain)", "Domain must be unique."),
    ]

    # Allow a single subdomain label (perlavillalari) or a FQDN
    # (perlavillalari.tcrm.online). Emails and spaces are rejected separately.
    _DOMAIN_RE = re.compile(
        r"^(?=.{1,253}$)(?!-)[a-z0-9-]+(?:\.[a-z0-9-]+)*$"
    )

    @api.model
    def _normalize_domain(self, value):
        d = (value or "").strip().lower().rstrip(".")
        if d.startswith("https://"):
            d = d[8:]
        elif d.startswith("http://"):
            d = d[7:]
        d = d.split("/")[0].split("?")[0]
        return d

    @api.constrains("domain")
    def _check_domain_format(self):
        for rec in self:
            d = self._normalize_domain(rec.domain)
            if not d:
                raise ValidationError(_("Domain is required."))
            if "@" in d:
                raise ValidationError(_(
                    "Domain cannot be an email address (got %r). "
                    "Use a hostname such as perlavillalari.tcrm.online."
                ) % (rec.domain,))
            if " " in d or not self._DOMAIN_RE.match(d):
                raise ValidationError(_(
                    "Invalid domain %r. Use a lowercase hostname like "
                    "tenant.tcrm.online (letters, digits, dots, hyphens)."
                ) % (rec.domain,))
            # Stored value must already be normalized by create/write.
            if d != (rec.domain or "").strip().lower().rstrip("."):
                raise ValidationError(_(
                    "Domain must be a normalized hostname (got %r)."
                ) % (rec.domain,))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("domain"):
                vals["domain"] = self._normalize_domain(vals["domain"])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("domain"):
            vals = dict(vals, domain=self._normalize_domain(vals["domain"]))
        return super().write(vals)

    @api.constrains("tenant_id", "is_primary", "active")
    def _check_single_primary(self):
        for rec in self.filtered(lambda r: r.is_primary and r.active):
            count = self.search_count(
                [("tenant_id", "=", rec.tenant_id.id), ("is_primary", "=", True), ("active", "=", True), ("id", "!=", rec.id)]
            )
            if count:
                raise ValidationError(_("Only one active primary domain is allowed per tenant."))


class TcrmTenantModuleEntitlement(models.Model):
    _name = "tcrm.tenant.module.entitlement"
    _description = "Tenant Module Entitlement"
    _order = "id desc"

    tenant_id = fields.Many2one("tcrm.tenant", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="tenant_id.company_id", store=True, readonly=True)
    module_id = fields.Many2one("ir.module.module", required=True, ondelete="cascade")
    state = fields.Selection([("allowed", "Allowed"), ("blocked", "Blocked"), ("trial", "Trial")], default="allowed", required=True)
    source = fields.Selection(
        [("package", "Package"), ("manual", "Manual"), ("provision", "Provision")],
        default="manual",
        required=True,
    )
    note = fields.Char(translate=True)

    _sql_constraints = [
        ("tcrm_tenant_module_uniq", "unique(tenant_id,module_id)", "Module entitlement already exists for this tenant."),
    ]


class TcrmTenantInvoice(models.Model):
    _name = "tcrm.tenant.invoice"
    _description = "Tenant Billing Invoice"
    _order = "id desc"

    name = fields.Char(default=lambda self: _("New"))
    tenant_id = fields.Many2one("tcrm.tenant", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="tenant_id.company_id", store=True, readonly=True)
    subscription_id = fields.Many2one("tcrm.tenant.subscription", ondelete="set null")
    issue_date = fields.Date(default=fields.Date.today, required=True)
    due_date = fields.Date(required=True)
    amount = fields.Monetary(required=True, currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", required=True, default=lambda self: self.env.company.currency_id.id)
    state = fields.Selection(
        [("draft", "Draft"), ("open", "Open"), ("paid", "Paid"), ("overdue", "Overdue"), ("cancelled", "Cancelled")],
        default="draft",
        required=True,
    )
    reminder_count = fields.Integer(default=0)
    last_reminder_date = fields.Date()
    notes = fields.Text(translate=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.name == _("New"):
                rec.name = self.env["ir.sequence"].next_by_code("tcrm.tenant.invoice") or _("New")
        return records

    def action_open(self):
        self.write({"state": "open"})

    def action_mark_paid(self):
        self.write({"state": "paid"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    @api.model
    def cron_generate_recurring_invoices(self):
        today = fields.Date.today()
        subscriptions = self.env["tcrm.tenant.subscription"].search(
            [("status", "in", ["trial", "active", "past_due"]), ("next_invoice_date", "<=", today), ("auto_renew", "=", True)]
        )
        for sub in subscriptions:
            exists = self.search_count(
                [("subscription_id", "=", sub.id), ("issue_date", "=", sub.next_invoice_date), ("state", "!=", "cancelled")]
            )
            if exists:
                continue
            self.create(
                {
                    "tenant_id": sub.tenant_id.id,
                    "subscription_id": sub.id,
                    "issue_date": sub.next_invoice_date,
                    "due_date": sub.next_invoice_date + relativedelta(days=7),
                    "amount": sub.amount,
                    "currency_id": sub.currency_id.id,
                    "state": "open",
                    "notes": _("Auto-generated by recurring billing."),
                }
            )
            step = relativedelta(months=1) if sub.billing_cycle == "monthly" else relativedelta(years=1)
            sub.next_invoice_date = sub.next_invoice_date + step

    @api.model
    def cron_mark_overdue_and_notify(self):
        today = fields.Date.today()
        invoices = self.search([("state", "in", ["open", "draft"]), ("due_date", "<", today)])
        for inv in invoices:
            inv.state = "overdue"
            if inv.last_reminder_date == today:
                continue
            inv.reminder_count += 1
            inv.last_reminder_date = today
            for user in inv.tenant_id.user_ids.filtered(lambda u: u.active):
                self.env["mail.activity"].sudo().create(
                    {
                        "res_model_id": self.env["ir.model"]._get_id("tcrm.tenant.invoice"),
                        "res_id": inv.id,
                        "user_id": user.id,
                        "summary": _("Payment reminder for %s") % inv.name,
                        "note": _("Invoice %s for tenant %s is overdue.") % (inv.name, inv.tenant_id.display_name),
                        "date_deadline": today,
                    }
                )
