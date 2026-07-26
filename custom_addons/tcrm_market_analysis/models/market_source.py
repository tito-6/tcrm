# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
import json
import logging

from tcrm import api, fields, models, _
from tcrm.exceptions import AccessError, UserError

from ..connectors import get_connector

_logger = logging.getLogger(__name__)


class TcrmMarketSource(models.Model):
    _name = "tcrm.market.source"
    _description = "Market Data Source"
    _order = "name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    source_type = fields.Selection(
        [
            ("rest", "REST API"),
            ("soap", "SOAP"),
            ("json", "JSON"),
            ("xml", "XML"),
            ("sftp", "SFTP"),
            ("csv", "CSV Upload"),
            ("xlsx", "XLSX Upload"),
            ("json_upload", "JSON Upload"),
            ("tenant_export", "Tenant Export"),
            ("demo", "Fictional Demo"),
            ("sahibinden", "Sahibinden (Public)"),
        ],
        required=True,
        default="csv",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("enabled", "Enabled"),
            ("disabled", "Disabled"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    authorization_state = fields.Selection(
        [
            ("unauthorized", "Unauthorized"),
            ("pending", "Pending Review"),
            ("authorized", "Authorized"),
            ("revoked", "Revoked"),
        ],
        default="unauthorized",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    # Secrets: stored but never exposed to list views / RPC helpers below.
    credential_ref = fields.Char(
        string="Credential Reference",
        help="Internal reference to a secret store entry. Never log the secret itself.",
        groups="tcrm_market_analysis.group_market_admin",
    )
    credential_secret = fields.Char(
        string="Credential Secret",
        groups="tcrm_market_analysis.group_market_admin",
        copy=False,
    )
    authorized_endpoint = fields.Char(
        string="Authorized Endpoint / Feed URL",
        groups="tcrm_market_analysis.group_market_admin",
    )
    authorization_evidence = fields.Text(
        string="Authorization Evidence",
        groups="tcrm_market_analysis.group_market_admin",
        help="Contract/license note or ticket reference proving permitted use.",
    )
    api_scope = fields.Char(string="Approved Scope", groups="tcrm_market_analysis.group_market_admin")
    capabilities_json = fields.Text(default="{}")
    capabilities_display = fields.Char(compute="_compute_capabilities_display")
    rate_limit_per_minute = fields.Integer(default=30)
    max_pages = fields.Integer(default=50)
    max_records = fields.Integer(default=5000)
    retention_days = fields.Integer(default=365)
    last_success_at = fields.Datetime()
    last_failure_at = fields.Datetime()
    last_error = fields.Text()
    rate_limit_state = fields.Selection(
        [("ok", "OK"), ("limited", "Limited"), ("unknown", "Unknown")],
        default="unknown",
    )
    health = fields.Selection(
        [("unknown", "Unknown"), ("healthy", "Healthy"), ("degraded", "Degraded"), ("error", "Error")],
        default="unknown",
        tracking=True,
    )
    mapping_version = fields.Char(default="1.0.0")
    kill_switch = fields.Boolean(default=False, tracking=True)
    import_job_ids = fields.One2many("tcrm.market.import.job", "source_id", string="Import Jobs")
    listing_count = fields.Integer(compute="_compute_listing_count")

    # Public collection filters (human place names — not internal IDs)
    filter_transaction = fields.Selection(
        [("sale", "Satılık"), ("rent", "Kiralık")],
        string="İşlem",
        default="sale",
    )
    filter_category = fields.Selection(
        [
            ("daire", "Daire"),
            ("residence", "Rezidans"),
            ("villa", "Villa"),
            ("mustakil-ev", "Müstakil Ev"),
            ("isyerleri", "İşyeri"),
            ("arsa", "Arsa"),
        ],
        string="Kategori",
        default="daire",
    )
    filter_province = fields.Char(string="İl")
    filter_district = fields.Char(string="İlçe")
    filter_neighborhood = fields.Char(string="Semt / Mahalle")
    fetch_details = fields.Boolean(
        string="Fetch Detail Pages",
        default=False,
        help="When enabled, opens each public listing page for richer attributes.",
    )
    schedule_enabled = fields.Boolean(string="Scheduled Runs", default=False)
    scrape_progress = fields.Float(string="Progress %", readonly=True)
    scrape_progress_message = fields.Char(readonly=True)
    scrape_state = fields.Selection(
        [
            ("idle", "Idle"),
            ("running", "Running"),
            ("done", "Done"),
            ("failed", "Failed"),
            ("blocked", "Blocked"),
        ],
        default="idle",
        readonly=True,
    )
    last_run_at = fields.Datetime(readonly=True)
    error_log = fields.Text(string="Error Log", readonly=True)
    # User-supplied browser Cookie header (manually pasted). Never harvested from the OS browser profile.
    browser_cookie = fields.Text(
        string="Browser Cookie / Request Headers",
        groups="tcrm_market_analysis.group_market_admin",
        copy=False,
        help=(
            "Optional. After YOU open https://www.sahibinden.com/satilik-daire successfully, "
            "paste either the Cookie header value OR the full Request Headers block from DevTools. "
            "Must come from the same browser request that returned HTTP 200 (include cf_clearance). "
            "TCRM must run from the same public IP as that browser. "
            "TCRM will not read your browser profile, solve CAPTCHA, or bypass Cloudflare."
        ),
    )
    browser_user_agent = fields.Char(
        string="Browser User-Agent",
        groups="tcrm_market_analysis.group_market_admin",
        copy=False,
        help=(
            "Required when using cookies. Paste the exact User-Agent from the SAME DevTools "
            "request as the Cookie (cf_clearance is bound to UA + IP)."
        ),
    )

    @api.depends("capabilities_json")
    def _compute_capabilities_display(self):
        for rec in self:
            try:
                caps = json.loads(rec.capabilities_json or "{}")
            except json.JSONDecodeError:
                caps = {}
            rec.capabilities_display = ", ".join(sorted(k for k, v in caps.items() if v)) or "—"

    def _compute_listing_count(self):
        Listing = self.env["tcrm.market.listing"]
        for rec in self:
            rec.listing_count = Listing.search_count([("source_id", "=", rec.id)])

    @api.model_create_multi
    def create(self, vals_list):
        from ..connectors.registry import get_connector as _gc  # noqa
        records = super().create(vals_list)
        for rec in records:
            if not rec.capabilities_json or rec.capabilities_json == "{}":
                try:
                    connector = get_connector(self.env, rec)
                    rec.capabilities_json = json.dumps(connector.DEFAULT_CAPABILITIES)
                except Exception:
                    pass
            if rec.source_type in ("demo", "sahibinden") and rec.authorization_state == "unauthorized":
                # Public/demo collectors do not require licensed API credentials.
                rec.authorization_state = "authorized"
        return records

    def get_secure_config(self) -> dict:
        """Admin-only secret bundle. Never call from list serializers."""
        self.ensure_one()
        if not self.env.user.has_group("tcrm_market_analysis.group_market_admin"):
            raise AccessError(_("Only Market Analysis Administrators can read source credentials."))
        return {
            "authorization_evidence": self.authorization_evidence or "",
            "api_endpoint": self.authorized_endpoint or "",
            "api_scope": self.api_scope or "",
            "credential_ref": self.credential_ref or "",
            # intentionally omit credential_secret from generic dumps unless needed by connector
            "has_secret": bool(self.credential_secret),
        }

    def action_enable(self):
        for rec in self:
            if rec.source_type == "sahibinden":
                connector = get_connector(self.env, rec)
                connector.validate_configuration()
            if rec.authorization_state != "authorized" and rec.source_type not in ("sahibinden", "demo"):
                raise UserError(_("Authorize the source before enabling."))
            if rec.source_type in ("sahibinden", "demo"):
                rec.authorization_state = "authorized"
            rec.write({"state": "enabled", "kill_switch": False, "active": True})

    def action_scrape_now(self):
        """Start an immediate public collection job for this source."""
        self.ensure_one()
        if self.source_type != "sahibinden":
            raise UserError(_("Scrape Now is only available for Sahibinden public sources."))
        if self.kill_switch or self.state != "enabled":
            raise UserError(_("Enable the source and clear kill switch before scraping."))
        from .market_import_job import TcrmMarketImportJob  # noqa: F401
        job = self.env["tcrm.market.import.job"].create({
            "source_id": self.id,
            "company_id": self.company_id.id,
            "job_type": "scrape",
            "tenant_db_name": self.env.cr.dbname,
            "name": _("Scrape Now — %s") % self.name,
        })
        self.write({
            "scrape_state": "running",
            "scrape_progress": 0,
            "scrape_progress_message": _("Starting…"),
            "error_log": False,
            "last_run_at": fields.Datetime.now(),
        })
        try:
            job.action_run()
        except UserError as exc:
            msg = str(exc)
            self.write({
                "scrape_state": "blocked" if any(x in msg.lower() for x in ("block", "cloudflare", "captcha", "403")) else "failed",
                "scrape_progress_message": msg[:500],
                "error_log": msg[:5000],
                "last_failure_at": fields.Datetime.now(),
                "last_error": msg[:2000],
                "health": "error",
            })
            raise
        except Exception as exc:
            msg = str(exc)
            self.write({
                "scrape_state": "failed",
                "scrape_progress_message": msg[:500],
                "error_log": msg[:5000],
                "last_failure_at": fields.Datetime.now(),
                "last_error": msg[:2000],
                "health": "error",
            })
            raise UserError(msg) from exc
        self.write({
            "scrape_state": "done" if job.state == "done" else job.state,
            "scrape_progress": 100,
            "scrape_progress_message": _("Finished: +%s / ~%s / skip %s") % (
                job.count_created, job.count_updated, job.count_skipped,
            ),
            "last_success_at": fields.Datetime.now(),
            "health": "healthy",
            "error_log": job.error_summary or False,
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "tcrm.market.import.job",
            "res_id": job.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_disable(self):
        self.write({"state": "disabled"})

    def action_kill_switch(self):
        self.write({"kill_switch": True, "state": "disabled"})

    def action_test_connection(self):
        self.ensure_one()
        connector = get_connector(self.env, self)
        if self.kill_switch:
            connector.kill()
        try:
            result = connector.test_connection()
        except UserError as exc:
            self.write({
                "last_failure_at": fields.Datetime.now(),
                "last_error": str(exc)[:2000],
                "error_log": str(exc)[:5000],
                "health": "error",
                "scrape_state": "blocked",
            })
            raise
        except Exception as exc:
            self.write({
                "last_failure_at": fields.Datetime.now(),
                "last_error": str(exc)[:2000],
                "health": "error",
            })
            raise UserError(str(exc)) from exc
        self.write({
            "last_success_at": fields.Datetime.now(),
            "last_error": False,
            "health": "healthy",
            "rate_limit_state": "ok",
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Connection test"),
                "message": result.get("message") or _("OK"),
                "type": "success",
                "sticky": False,
            },
        }

    def read(self, fields=None, load="_classic_read"):
        """Strip secrets from non-admin reads even if fields requested."""
        rows = super().read(fields=fields, load=load)
        if self.env.user.has_group("tcrm_market_analysis.group_market_admin"):
            return rows
        secret_fields = {
            "credential_secret", "credential_ref", "authorization_evidence",
            "api_scope", "browser_cookie",
        }
        for row in rows:
            for key in secret_fields:
                if key in row:
                    row[key] = False
        return rows
