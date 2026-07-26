# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
from tcrm import models, _


class PropertioProjectMarket(models.Model):
    _inherit = "propertio.project"

    def action_open_market_analysis(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "tcrm_market_analysis.app",
            "name": _("Piyasa Analizi"),
            "params": {
                "section": "overview",
                "project_id": self.id,
                "province": self.city or "",
            },
        }
