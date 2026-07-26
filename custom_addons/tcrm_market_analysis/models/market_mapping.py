# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
from tcrm import api, fields, models


class TcrmMarketMapping(models.Model):
    _name = "tcrm.market.mapping"
    _description = "Market Taxonomy Mapping"
    _order = "map_type, source_value"

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    source_id = fields.Many2one("tcrm.market.source", ondelete="cascade")
    map_type = fields.Selection(
        [
            ("transaction", "Transaction"),
            ("category", "Category"),
            ("subcategory", "Subcategory"),
            ("province", "Province"),
            ("district", "District"),
            ("neighborhood", "Neighborhood"),
            ("currency", "Currency"),
            ("room_type", "Room Type"),
            ("heating", "Heating"),
            ("building_age", "Building Age"),
            ("use_status", "Use Status"),
            ("title_deed", "Title Deed"),
            ("seller_type", "Seller Type"),
            ("amenity", "Amenity"),
        ],
        required=True,
        index=True,
    )
    source_value = fields.Char(required=True, index=True)
    target_value = fields.Char(required=True)
    active = fields.Boolean(default=True)
    mapping_version = fields.Char(default="1.0.0")

    _sql_constraints = [
        (
            "tcrm_market_mapping_uniq",
            "unique(company_id, source_id, map_type, source_value)",
            "Mapping already exists for this source value.",
        ),
    ]

    @api.depends("map_type", "source_value", "target_value")
    def _compute_name(self):
        for rec in self:
            rec.name = "%s: %s → %s" % (rec.map_type, rec.source_value, rec.target_value)
