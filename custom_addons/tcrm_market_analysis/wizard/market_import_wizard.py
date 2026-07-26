# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
from tcrm import fields, models, _
from tcrm.exceptions import UserError


class TcrmMarketImportWizard(models.TransientModel):
    _name = "tcrm.market.import.wizard"
    _description = "Market Import Wizard"

    source_id = fields.Many2one(
        "tcrm.market.source",
        required=True,
        domain="[('authorization_state', '=', 'authorized'), ('state', '=', 'enabled')]",
    )
    data_file = fields.Binary(required=True)
    data_filename = fields.Char()
    dry_run = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )

    def action_preview(self):
        self.ensure_one()
        job = self.env["tcrm.market.import.job"].create({
            "source_id": self.source_id.id,
            "company_id": self.company_id.id,
            "data_file": self.data_file,
            "data_filename": self.data_filename,
            "dry_run": True,
            "job_type": "import",
            "tenant_db_name": self.env.cr.dbname,
        })
        job.action_preview()
        return {
            "type": "ir.actions.act_window",
            "res_model": "tcrm.market.import.job",
            "res_id": job.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_import(self):
        self.ensure_one()
        if self.source_id.source_type == "sahibinden":
            raise UserError(_("Sahibinden imports are refused without a licensed feed client."))
        job = self.env["tcrm.market.import.job"].create({
            "source_id": self.source_id.id,
            "company_id": self.company_id.id,
            "data_file": self.data_file,
            "data_filename": self.data_filename,
            "dry_run": self.dry_run,
            "job_type": "import",
            "tenant_db_name": self.env.cr.dbname,
        })
        job.action_run()
        return {
            "type": "ir.actions.act_window",
            "res_model": "tcrm.market.import.job",
            "res_id": job.id,
            "view_mode": "form",
            "target": "current",
        }
