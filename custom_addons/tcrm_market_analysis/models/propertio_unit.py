# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
from tcrm import fields, models, _


class PropertioUnitMarket(models.Model):
    _inherit = "propertio.unit"

    market_comparable_set_ids = fields.One2many("tcrm.market.comparable.set", "unit_id")
    market_comparable_count = fields.Integer(compute="_compute_market_comparable_count")

    def _compute_market_comparable_count(self):
        for unit in self:
            unit.market_comparable_count = len(unit.market_comparable_set_ids)

    def action_open_market_comparables(self):
        self.ensure_one()
        Comparable = self.env["tcrm.market.comparable.set"]
        existing = Comparable.search([
            ("unit_id", "=", self.id),
            ("company_id", "=", self.company_id.id),
        ], limit=1)
        if not existing:
            existing = Comparable.create({
                "name": _("Emsal — %s") % self.display_name,
                "unit_id": self.id,
                "project_id": self.project_id.id,
                "company_id": self.company_id.id,
            })
            existing.action_build_from_unit()
        return {
            "type": "ir.actions.act_window",
            "name": _("Emsal Analizi"),
            "res_model": "tcrm.market.comparable.set",
            "res_id": existing.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_market_analysis(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "tcrm_market_analysis.app",
            "name": _("Piyasa Analizi"),
            "params": {
                "section": "comparables",
                "unit_id": self.id,
                "project_id": self.project_id.id,
                "province": self.project_id.city or "",
            },
        }
