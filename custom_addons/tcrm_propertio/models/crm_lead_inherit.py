# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""
TCRM / Propertio: 5-Star Lead Priority (Turkish market expectation).
Base CRM uses 0-3; we extend with selection_add to 4 and 5 for 5-star system.

Also adds cross-module bridge fields so a CRM opportunity can reference the
Propertio project / unit it is about, and expose the resulting property sale
contracts, making records traceable across CRM, Properties and Sales.
"""

from tcrm import api, fields, models


class CrmLeadInherit(models.Model):
    _inherit = 'crm.lead'

    priority = fields.Selection(
        selection_add=[
            ('4', '★★★★'),
            ('5', '★★★★★'),
        ],
        ondelete={'4': 'set default', '5': 'set default'},
    )

    # --- Propertio cross-module bridge ---------------------------------------
    propertio_project_id = fields.Many2one(
        'propertio.project', string='Gayrimenkul Projesi', index=True,
        help='Bu fırsatın ilgili olduğu gayrimenkul projesi.')
    propertio_unit_id = fields.Many2one(
        'propertio.unit', string='Gayrimenkul Birimi', index=True,
        domain="['|', ('project_id', '=', propertio_project_id), ('project_id', '!=', False)]",
        help='Bu fırsatın hedeflediği birim.')
    propertio_sale_ids = fields.One2many(
        'propertio.sale', 'opportunity_id', string='Gayrimenkul Sözleşmeleri')
    propertio_sale_count = fields.Integer(
        string='Sözleşme Sayısı', compute='_compute_propertio_sale_count')

    @api.depends('propertio_sale_ids')
    def _compute_propertio_sale_count(self):
        for lead in self:
            lead.propertio_sale_count = len(lead.propertio_sale_ids)

    def action_view_propertio_sales(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Gayrimenkul Sözleşmeleri',
            'res_model': 'propertio.sale',
            'view_mode': 'list,form',
            'domain': [('opportunity_id', '=', self.id)],
            'context': {'default_opportunity_id': self.id,
                        'default_partner_id': self.partner_id.id},
        }
