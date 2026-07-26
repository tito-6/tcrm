# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
from tcrm import api, fields, models


class TcrmMarketSeller(models.Model):
    _name = "tcrm.market.seller"
    _description = "Market Seller (Organization / Pseudonymous)"
    _order = "name"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    source_id = fields.Many2one("tcrm.market.source", required=True, ondelete="cascade", index=True)
    seller_type = fields.Char(default="unknown", index=True)
    external_id = fields.Char(required=True, index=True)
    display_name_licensed = fields.Char(
        string="Licensed Business Display Name",
        help="Only store when permitted. Individuals use pseudonymous identifiers.",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Linked Broker/Agency",
        help="Manual confirmed link only. Never auto-created from private listing data.",
    )
    first_observed_at = fields.Datetime()
    last_observed_at = fields.Datetime()
    active_listing_count = fields.Integer(compute="_compute_active_listing_count")
    listing_ids = fields.One2many("tcrm.market.listing", "seller_id")

    _sql_constraints = [
        (
            "tcrm_market_seller_uniq",
            "unique(company_id, source_id, external_id)",
            "Seller external ID must be unique per source and company.",
        ),
    ]

    def _compute_active_listing_count(self):
        for rec in self:
            rec.active_listing_count = self.env["tcrm.market.listing"].search_count([
                ("seller_id", "=", rec.id),
                ("state", "=", "active"),
            ])

    @api.model
    def _upsert_from_import(self, company_id, source, external_id, seller_type, display_name=False):
        external_id = str(external_id)
        existing = self.search([
            ("company_id", "=", company_id),
            ("source_id", "=", source.id),
            ("external_id", "=", external_id),
        ], limit=1)
        now = fields.Datetime.now()
        # Pseudonymous default for private individuals
        is_private = (seller_type or "").lower() in ("owner", "individual", "sahibinden", "private")
        name = display_name if display_name and not is_private else ("seller:%s" % external_id[-12:])
        vals = {
            "name": name,
            "company_id": company_id,
            "source_id": source.id,
            "external_id": external_id,
            "seller_type": seller_type or "unknown",
            "display_name_licensed": display_name if display_name and not is_private else False,
            "last_observed_at": now,
        }
        if existing:
            existing.write(vals)
            return existing
        vals["first_observed_at"] = now
        return self.create(vals)
