# -*- coding: utf-8 -*-
# Part of Tcrm. See LICENSE file for full copyright and licensing details.

from tcrm import api, models


class PurchaseRequisitionCreateAlternative(models.TransientModel):
    _inherit = 'purchase.requisition.create.alternative'

    @api.model
    def _get_alternative_line_value(self, order_line, product_tmpl_ids_with_description):
        res_line = super()._get_alternative_line_value(order_line, product_tmpl_ids_with_description)
        if order_line.sale_line_id:
            res_line['sale_line_id'] = order_line.sale_line_id.id

        return res_line
