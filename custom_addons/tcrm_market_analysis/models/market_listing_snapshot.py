# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
from tcrm import fields, models


class TcrmMarketListingSnapshot(models.Model):
    _name = "tcrm.market.listing.snapshot"
    _description = "Market Listing Observation Snapshot"
    _order = "observed_at desc, id desc"

    listing_id = fields.Many2one(
        "tcrm.market.listing", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    observed_at = fields.Datetime(required=True, index=True)
    asking_price = fields.Float(string="Asking Price", required=True)
    currency_name = fields.Char(required=True, default="TRY")
    gross_area = fields.Float()
    net_area = fields.Float()
    gross_price_m2 = fields.Float()
    state = fields.Char()
    checksum = fields.Char(index=True)
    import_job_id = fields.Many2one("tcrm.market.import.job", ondelete="set null")
    change_flags = fields.Char()
    mutable_json = fields.Text()
