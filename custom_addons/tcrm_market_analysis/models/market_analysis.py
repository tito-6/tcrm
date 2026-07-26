# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
import json

from tcrm import api, fields, models, _


class TcrmMarketAnalysis(models.Model):
    _name = "tcrm.market.analysis"
    _description = "Saved Market Analysis"
    _order = "id desc"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    description = fields.Text()
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True)
    visibility = fields.Selection(
        [("private", "Private"), ("company", "Company")],
        default="private",
        required=True,
    )
    filter_json = fields.Text(default="{}")
    date_from = fields.Date()
    date_to = fields.Date()
    metrics_json = fields.Text()
    last_calculated_at = fields.Datetime()
    share_user_ids = fields.Many2many("res.users", string="Shared With")
    schedule_report = fields.Boolean(default=False)
    opportunity_id = fields.Many2one("crm.lead", string="CRM Opportunity")
    project_id = fields.Many2one("propertio.project")
    unit_id = fields.Many2one("propertio.unit")
    sale_id = fields.Many2one("propertio.sale")

    def action_calculate(self):
        Listing = self.env["tcrm.market.listing"]
        for rec in self:
            try:
                filters = json.loads(rec.filter_json or "{}")
            except json.JSONDecodeError:
                filters = {}
            domain = [("company_id", "=", rec.company_id.id), ("state", "=", "active")]
            for key in ("transaction_type", "category_code", "province", "district", "neighborhood"):
                if filters.get(key):
                    domain.append((key, "=", filters[key]))
            if filters.get("price_min"):
                domain.append(("asking_price", ">=", float(filters["price_min"])))
            if filters.get("price_max"):
                domain.append(("asking_price", "<=", float(filters["price_max"])))
            metrics = Listing.get_overview_metrics(domain)
            rec.write({
                "metrics_json": json.dumps(metrics, default=str),
                "last_calculated_at": fields.Datetime.now(),
            })
        return True

    def action_open_app(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "tcrm_market_analysis.app",
            "name": _("Piyasa Analizi"),
            "params": {
                "section": "saved",
                "analysis_id": self.id,
            },
        }
