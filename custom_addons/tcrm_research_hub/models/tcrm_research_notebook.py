# -*- coding: utf-8 -*-
import json

from tcrm import api, fields, models, _
from tcrm.exceptions import UserError

from . import notebooklm_client


class TcrmResearchNotebook(models.Model):
    _name = "tcrm.research.notebook"
    _description = "Synced NotebookLM Research"
    _order = "synced_at desc, name"

    name = fields.Char(required=True, index=True)
    google_notebook_id = fields.Char(required=True, index=True)
    description = fields.Text()
    url = fields.Char(string="NotebookLM URL")
    source_count = fields.Integer(string="Sources")
    user_id = fields.Many2one(
        "res.users",
        string="Owner",
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    synced_at = fields.Datetime(string="Last Synced")
    raw_payload = fields.Text(string="Raw Payload")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "uniq_user_google_notebook",
            "unique(user_id, google_notebook_id)",
            "This NotebookLM research is already synced for this user.",
        ),
    ]

    def action_open_in_google(self):
        self.ensure_one()
        url = self.url or f"{notebooklm_client.NOTEBOOK_ORIGIN}/notebook/{self.google_notebook_id}"
        return {"type": "ir.actions.act_url", "url": url, "target": "new"}

    @api.model
    def action_sync_from_google(self):
        """Sync current user's NotebookLM notebooks into this model."""
        from . import session_jar

        uid = self.env.uid
        sess = session_jar.load_session(uid)
        SyncLog = self.env["tcrm.research.sync.log"].sudo()
        log = SyncLog.search([("user_id", "=", uid)], limit=1)
        if not log:
            log = SyncLog.create({"user_id": uid})

        try:
            notebooks = notebooklm_client.list_notebooks(sess)
            session_jar.save_session(uid, sess)
        except notebooklm_client.NotebookLMClientError as exc:
            log.write({
                "state": "error",
                "message": str(exc),
                "last_sync_at": fields.Datetime.now(),
                "notebook_count": 0,
            })
            raise UserError(str(exc)) from exc
        except Exception as exc:
            log.write({
                "state": "error",
                "message": str(exc),
                "last_sync_at": fields.Datetime.now(),
            })
            raise UserError(_("NotebookLM sync failed: %s") % exc) from exc

        now = fields.Datetime.now()
        Notebook = self.sudo()
        seen_ids = []
        for nb in notebooks:
            gid = nb["google_notebook_id"]
            seen_ids.append(gid)
            vals = {
                "name": nb.get("name") or gid,
                "description": nb.get("description") or "",
                "url": nb.get("url") or "",
                "source_count": int(nb.get("source_count") or 0),
                "synced_at": now,
                "raw_payload": json.dumps(nb.get("raw") or {}, default=str)[:50000],
                "user_id": uid,
                "company_id": self.env.company.id,
                "active": True,
            }
            existing = Notebook.search([
                ("user_id", "=", uid),
                ("google_notebook_id", "=", gid),
            ], limit=1)
            if existing:
                existing.write(vals)
            else:
                vals["google_notebook_id"] = gid
                Notebook.create(vals)

        # Soft-archive notebooks that disappeared from Google
        stale = Notebook.search([
            ("user_id", "=", uid),
            ("google_notebook_id", "not in", seen_ids or ["__none__"]),
        ])
        if stale:
            stale.write({"active": False})

        log.write({
            "state": "ok",
            "message": _("Synced %s researches.") % len(notebooks),
            "last_sync_at": now,
            "notebook_count": len(notebooks),
        })
        return {
            "count": len(notebooks),
            "last_sync_at": fields.Datetime.to_string(now),
            "message": log.message,
        }


class TcrmResearchSyncLog(models.Model):
    _name = "tcrm.research.sync.log"
    _description = "NotebookLM Sync Status"
    _order = "last_sync_at desc"

    user_id = fields.Many2one("res.users", required=True, index=True, ondelete="cascade")
    state = fields.Selection([
        ("ok", "OK"),
        ("error", "Error"),
        ("pending", "Pending"),
    ], default="pending")
    message = fields.Char()
    last_sync_at = fields.Datetime()
    notebook_count = fields.Integer()
