# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import models


class ReportMrpReport_Mo_Overview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _get_unit_cost(self, move):
        if move.state == 'done':
            price_unit = move._get_price_unit()
            return move.product_id.uom_id._compute_price(price_unit, move.product_uom)
        return super()._get_unit_cost(move)
