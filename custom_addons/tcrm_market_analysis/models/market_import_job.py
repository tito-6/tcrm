# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
import base64
import logging

from tcrm import api, fields, models, _
from tcrm.exceptions import UserError

from ..connectors import get_connector
from ..services.import_pipeline import ImportPipeline, file_checksum

_logger = logging.getLogger(__name__)


class TcrmMarketImportJob(models.Model):
    _name = "tcrm.market.import.job"
    _description = "Market Import / Sync Job"
    _order = "id desc"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, default=lambda self: _("New"), copy=False)
    source_id = fields.Many2one("tcrm.market.source", required=True, index=True, ondelete="restrict")
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    tenant_db_name = fields.Char(
        string="Tenant Database",
        help="Explicit database name this job targeted. Never fan-out across DBs.",
        index=True,
        readonly=True,
    )
    requester_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True)
    job_type = fields.Selection(
        [
            ("import", "Import"),
            ("sync", "Sync"),
            ("demo_seed", "Demo Seed"),
            ("scrape", "Scrape Now"),
        ],
        default="import",
        required=True,
    )
    progress = fields.Float(string="Progress %", readonly=True)
    progress_message = fields.Char(readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("preview", "Preview"),
            ("running", "Running"),
            ("done", "Done"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    date_start = fields.Datetime()
    date_end = fields.Datetime()
    input_filename = fields.Char()
    input_checksum = fields.Char(index=True)
    data_file = fields.Binary(attachment=True)
    data_filename = fields.Char()
    dry_run = fields.Boolean(default=False)
    count_read = fields.Integer()
    count_created = fields.Integer()
    count_updated = fields.Integer()
    count_skipped = fields.Integer()
    count_rejected = fields.Integer()
    warning_summary = fields.Text()
    error_summary = fields.Text()
    parser_version = fields.Char()
    mapping_version = fields.Char()
    retry_count = fields.Integer(default=0)
    preview_json = fields.Text()
    kill_requested = fields.Boolean(default=False)

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) in (False, _("New"), "New"):
                vals["name"] = seq.next_by_code("tcrm.market.import.job") or _("Import")
            vals.setdefault("tenant_db_name", self.env.cr.dbname)
        return super().create(vals_list)

    def action_cancel(self):
        self.write({"state": "cancelled", "kill_requested": True})

    def action_preview(self):
        self.ensure_one()
        rows = self._load_rows()
        pipeline = ImportPipeline(self.env, self.source_id, self, dry_run=True, company_id=self.company_id.id)
        preview = pipeline.preview(rows)
        import json
        self.write({
            "state": "preview",
            "preview_json": json.dumps(preview, default=str),
            "count_read": preview["total"],
            "parser_version": preview["parser_version"],
            "mapping_version": preview["mapping_version"],
        })
        return True

    def action_run(self):
        for job in self:
            if job.source_id.kill_switch or job.kill_requested:
                raise UserError(_("Kill switch is active for this source/job."))
            if job.source_id.authorization_state != "authorized" and job.job_type not in ("scrape", "demo_seed"):
                raise UserError(_("Source is not authorized."))
            if job.source_id.state != "enabled" and job.job_type not in ("demo_seed",):
                raise UserError(_("Source must be enabled."))
            # Explicit tenant DB binding — refuse silent cross-DB execution.
            if job.tenant_db_name and job.tenant_db_name != job.env.cr.dbname:
                raise UserError(
                    _("Job targets database '%s' but current DB is '%s'.")
                    % (job.tenant_db_name, job.env.cr.dbname)
                )
            try:
                job.write({
                    "state": "running",
                    "date_start": fields.Datetime.now(),
                    "progress": 5,
                    "progress_message": _("Loading rows…"),
                })
                rows = job._load_rows()
                job.write({
                    "progress": 40,
                    "progress_message": _("Importing %s rows…") % len(rows),
                })
                pipeline = ImportPipeline(
                    job.env,
                    job.source_id,
                    job,
                    dry_run=job.dry_run,
                    company_id=job.company_id.id,
                )
                pipeline.run(rows)
                # Mark listings missing from this scrape as removed_from_source (not sold)
                if job.job_type == "scrape" and not job.dry_run:
                    job._mark_missing_removed(rows)
                job.write({
                    "progress": 100,
                    "progress_message": _("Done"),
                })
            except UserError:
                raise
            except Exception as exc:
                _logger.exception("market import failed job=%s", job.id)
                err = str(exc)[:2000]
                job.write({
                    "state": "failed",
                    "date_end": fields.Datetime.now(),
                    "error_summary": err,
                    "retry_count": job.retry_count + 1,
                    "progress_message": err[:500],
                })
                job.source_id.write({
                    "last_failure_at": fields.Datetime.now(),
                    "last_error": err,
                    "error_log": err,
                    "health": "error",
                    "scrape_state": "blocked" if "block" in err.lower() or "captcha" in err.lower() else "failed",
                    "scrape_progress_message": err[:500],
                })
                raise UserError(err) from exc
        return True

    def action_retry(self):
        self.write({"state": "draft", "kill_requested": False, "error_summary": False})
        return self.action_run()

    def _load_rows(self):
        self.ensure_one()
        source = self.source_id
        connector = get_connector(self.env, source)
        if self.job_type == "demo_seed":
            from ..services.demo_seed import generate_demo_rows
            scenario = "istanbul" if "istanbul" in (source.name or "").lower() else "ankara_izmir"
            return generate_demo_rows(scenario=scenario, company_marker=self.company_id.name or "A")

        if self.job_type in ("scrape", "sync") and source.source_type == "sahibinden":
            def _progress(pages, count, exhausted):
                pct = min(90.0, 10.0 + pages * 15.0)
                self.write({
                    "progress": pct,
                    "progress_message": _("Page %s — %s listings") % (pages, count),
                })
                source.write({
                    "scrape_progress": pct,
                    "scrape_progress_message": _("Page %s — %s listings") % (pages, count),
                    "scrape_state": "running",
                })

            return connector.collect(
                max_pages=source.max_pages or 5,
                max_records=source.max_records or 100,
                fetch_details=bool(source.fetch_details),
                progress_callback=_progress,
            )

        if not self.data_file:
            raise UserError(_("Upload a file or use scrape / demo seed job type."))
        data = base64.b64decode(self.data_file)
        checksum = file_checksum(data)
        self.input_checksum = checksum
        self.input_filename = self.data_filename or self.input_filename

        stype = source.source_type
        if stype == "json_upload":
            stype = "json"
        if stype in ("csv", "xlsx", "json"):
            from ..connectors.registry import _REGISTRY
            cls = _REGISTRY.get(stype)
            if not cls:
                raise UserError(_("No connector for type %s") % stype)
            parser = cls(self.env, source)
            return parser.parse_bytes(data)
        raise UserError(_("Source type '%s' does not support file upload in this job.") % source.source_type)

    def _mark_missing_removed(self, rows):
        """Listings not seen in this scrape → removed_from_source (never auto-sold)."""
        self.ensure_one()
        seen_ids = {str(r.get("external_id") or r.get("external_listing_id")) for r in rows if r.get("external_id") or r.get("external_listing_id")}
        seen_urls = {r.get("permitted_source_url") or r.get("url") for r in rows if r.get("permitted_source_url") or r.get("url")}
        Listing = self.env["tcrm.market.listing"]
        active = Listing.search([
            ("company_id", "=", self.company_id.id),
            ("source_id", "=", self.source_id.id),
            ("state", "=", "active"),
        ])
        for listing in active:
            if listing.external_listing_id in seen_ids:
                continue
            if listing.permitted_source_url and listing.permitted_source_url in seen_urls:
                continue
            listing.action_mark_removed_from_source()

    @api.model
    def _cron_process_due_syncs(self):
        """Cron entry: operate only on the current database (never fan-out)."""
        dbname = self.env.cr.dbname
        _logger.info("market sync cron on db=%s", dbname)
        sources = self.env["tcrm.market.source"].search([
            ("state", "=", "enabled"),
            ("kill_switch", "=", False),
            ("schedule_enabled", "=", True),
            ("source_type", "in", ("demo", "sahibinden")),
        ])
        for source in sources:
            job_type = "scrape" if source.source_type == "sahibinden" else "demo_seed"
            job = self.create({
                "source_id": source.id,
                "company_id": source.company_id.id,
                "job_type": job_type,
                "tenant_db_name": dbname,
            })
            try:
                source.write({"last_run_at": fields.Datetime.now(), "scrape_state": "running"})
                job.action_run()
                source.write({"scrape_state": "done", "last_success_at": fields.Datetime.now()})
            except Exception as exc:
                _logger.exception("cron sync failed source=%s db=%s", source.id, dbname)
                source.write({
                    "scrape_state": "failed",
                    "error_log": str(exc)[:5000],
                    "last_error": str(exc)[:2000],
                })
