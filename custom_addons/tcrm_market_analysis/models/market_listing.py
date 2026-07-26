# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
from tcrm import api, fields, models, _


class TcrmMarketListing(models.Model):
    _name = "tcrm.market.listing"
    _description = "Normalized Market Listing"
    _order = "last_observed_at desc, id desc"
    _inherit = ["mail.thread"]

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    source_id = fields.Many2one("tcrm.market.source", required=True, index=True, ondelete="restrict")
    external_listing_id = fields.Char(required=True, index=True)
    permitted_source_url = fields.Char()
    tenant_db_name = fields.Char(index=True, readonly=True)

    first_observed_at = fields.Datetime(index=True)
    last_observed_at = fields.Datetime(index=True)
    source_listing_date = fields.Date()
    state = fields.Selection(
        [
            ("active", "Active"),
            ("removed_from_source", "Removed From Source"),
            ("expired", "Expired"),
            ("inactive", "Inactive"),
        ],
        default="active",
        required=True,
        index=True,
        help="Removed listings are NOT automatically marked sold. Asking prices only.",
    )

    transaction_type = fields.Selection(
        [("sale", "Sale"), ("rent", "Rent"), ("short_term_rent", "Short-term Rent")],
        required=True,
        index=True,
    )
    category_code = fields.Char(required=True, index=True)
    subcategory_code = fields.Char(index=True)
    title = fields.Char()

    province = fields.Char(index=True)
    district = fields.Char(index=True)
    neighborhood = fields.Char(index=True)
    source_location_text = fields.Char()
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))

    currency_name = fields.Char(default="TRY", required=True)
    asking_price = fields.Float(
        string="Asking Price",
        required=True,
        help="Asking price (not a completed transaction price).",
    )
    gross_area = fields.Float()
    net_area = fields.Float()
    gross_price_m2 = fields.Float(string="Asking Price / Gross m²")
    net_price_m2 = fields.Float(string="Asking Price / Net m²")

    rooms = fields.Char()
    bedrooms = fields.Float()
    bathrooms = fields.Float()
    building_age = fields.Char()
    floor = fields.Char()
    total_floors = fields.Char()
    heating = fields.Char()
    kitchen = fields.Char()
    balcony = fields.Boolean()
    elevator = fields.Boolean()
    parking = fields.Char()
    furnished = fields.Char()
    use_status = fields.Char()
    in_compound = fields.Boolean()
    mortgage_eligible = fields.Boolean()
    title_deed_status = fields.Char()
    exchange_possible = fields.Boolean()

    seller_type = fields.Char(default="unknown")
    seller_id = fields.Many2one("tcrm.market.seller", index=True, ondelete="set null")
    media_count = fields.Integer(default=0)
    image_urls_json = fields.Text(
        string="Image URLs (JSON)",
        help="Permitted public image URLs only; never store private media without license.",
    )

    quality_score = fields.Float(default=50.0)
    quality_status = fields.Selection(
        [("ok", "OK"), ("warning", "Warning"), ("error", "Error")],
        default="ok",
    )
    quality_notes = fields.Char()
    duplicate_cluster = fields.Char(index=True)
    is_outlier = fields.Boolean(default=False)
    source_checksum = fields.Char(index=True)
    import_job_id = fields.Many2one("tcrm.market.import.job", ondelete="set null")
    parser_version = fields.Char()
    mapping_version = fields.Char()

    listing_age_days = fields.Integer(compute="_compute_age_metrics", store=False)
    days_on_market_est = fields.Integer(
        string="Estimated Days on Market",
        compute="_compute_age_metrics",
        store=False,
        help="Estimated from first/last observed; not a proven transaction date.",
    )
    snapshot_ids = fields.One2many("tcrm.market.listing.snapshot", "listing_id", string="Snapshots")
    snapshot_count = fields.Integer(compute="_compute_snapshot_count")

    _sql_constraints = [
        (
            "tcrm_market_listing_source_ext_uniq",
            "unique(company_id, source_id, external_listing_id)",
            "External listing ID must be unique per source and company.",
        ),
    ]

    @api.depends("title", "external_listing_id", "province", "district")
    def _compute_name(self):
        for rec in self:
            base = rec.title or rec.external_listing_id or _("Listing")
            loc = " / ".join(p for p in (rec.province, rec.district) if p)
            rec.name = "%s — %s" % (base, loc) if loc else base

    def _compute_age_metrics(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.first_observed_at:
                delta = now - rec.first_observed_at
                rec.listing_age_days = max(0, delta.days)
                if rec.state == "active":
                    rec.days_on_market_est = rec.listing_age_days
                elif rec.last_observed_at:
                    rec.days_on_market_est = max(0, (rec.last_observed_at - rec.first_observed_at).days)
                else:
                    rec.days_on_market_est = rec.listing_age_days
            else:
                rec.listing_age_days = 0
                rec.days_on_market_est = 0

    def _compute_snapshot_count(self):
        for rec in self:
            rec.snapshot_count = len(rec.snapshot_ids)

    def action_mark_removed_from_source(self):
        """Lifecycle: removed ≠ sold."""
        self.write({"state": "removed_from_source"})

    @api.model
    def _recompute_duplicate_clusters(self, company_id=None):
        company_id = company_id or self.env.company.id
        listings = self.search([
            ("company_id", "=", company_id),
            ("state", "=", "active"),
            ("asking_price", ">", 0),
        ])
        buckets = {}
        for listing in listings:
            key = "|".join([
                listing.transaction_type or "",
                listing.category_code or "",
                (listing.province or "").lower(),
                (listing.district or "").lower(),
                (listing.neighborhood or "").lower(),
                str(round(listing.asking_price or 0, -3)),
                str(round(listing.gross_area or 0)),
                listing.rooms or "",
            ])
            buckets.setdefault(key, self.env["tcrm.market.listing"])
            buckets[key] |= listing
        for key, group in buckets.items():
            if len(group) > 1:
                cluster = "dup:%s" % (abs(hash(key)) % (10 ** 10))
                group.write({"duplicate_cluster": cluster})
            else:
                group.write({"duplicate_cluster": False})

    @api.model
    def get_overview_metrics(self, domain=None):
        from ..services.analytics import summarize_prices, mean, median

        domain = list(domain or [])
        domain.append(("company_id", "in", self.env.companies.ids))
        active = self.search(domain + [("state", "=", "active")])
        if not active:
            return {
                "empty": True,
                "message": "No authorized market data loaded",
                "active_count": 0,
            }
        prices = active.mapped("asking_price")
        ppm2 = [p for p in active.mapped("gross_price_m2") if p]
        ages = [a for a in active.mapped("listing_age_days")]
        # Force compute ages
        active._compute_age_metrics()
        ages = [rec.listing_age_days for rec in active]
        removed = self.search_count(domain + [("state", "=", "removed_from_source")])
        summary = summarize_prices(prices)
        return {
            "empty": False,
            "active_count": len(active),
            "removed_count": removed,
            "asking_price": summary,
            "median_price_m2": median(ppm2),
            "mean_price_m2": mean(ppm2),
            "median_listing_age": median(ages),
            "label": "All monetary figures are asking prices, not completed transactions.",
        }
