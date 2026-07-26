# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
from tcrm import fields, models, _


class PropertioSaleMarket(models.Model):
    _inherit = "propertio.sale"

    market_analysis_ids = fields.One2many("tcrm.market.analysis", "sale_id")

    def action_open_market_context(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "tcrm_market_analysis.app",
            "name": _("Piyasa Analizi"),
            "params": {
                "section": "overview",
                "sale_id": self.id,
                "unit_id": self.unit_id.id,
                "project_id": self.project_id.id if self.project_id else False,
                "province": self.project_id.city if self.project_id else "",
            },
        }
