# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
from tcrm import fields, models, _


class CrmLeadMarket(models.Model):
    _inherit = "crm.lead"

    market_analysis_ids = fields.One2many("tcrm.market.analysis", "opportunity_id")
    market_analysis_count = fields.Integer(compute="_compute_market_analysis_count")

    def _compute_market_analysis_count(self):
        for lead in self:
            lead.market_analysis_count = len(lead.market_analysis_ids)

    def action_open_market_analysis(self):
        self.ensure_one()
        city = False
        if self.propertio_project_id:
            city = self.propertio_project_id.city
        return {
            "type": "ir.actions.client",
            "tag": "tcrm_market_analysis.app",
            "name": _("Piyasa Analizi"),
            "params": {
                "section": "explorer",
                "opportunity_id": self.id,
                "province": city or "",
                "unit_id": self.propertio_unit_id.id if self.propertio_unit_id else False,
                "project_id": self.propertio_project_id.id if self.propertio_project_id else False,
            },
        }
