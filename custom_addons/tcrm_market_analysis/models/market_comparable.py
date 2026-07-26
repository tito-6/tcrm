# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
import json

from tcrm import api, fields, models, _

from ..services.analytics import comparable_score, median, percentile, summarize_prices


class TcrmMarketComparableSet(models.Model):
    _name = "tcrm.market.comparable.set"
    _description = "Market Comparable Set"
    _order = "id desc"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    unit_id = fields.Many2one("propertio.unit", string="Subject Unit")
    project_id = fields.Many2one("propertio.project")
    opportunity_id = fields.Many2one("crm.lead")
    sale_id = fields.Many2one("propertio.sale")
    analysis_id = fields.Many2one("tcrm.market.analysis")
    line_ids = fields.One2many("tcrm.market.comparable.line", "set_id", string="Comparables")
    summary_json = fields.Text()
    confidence = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High")],
        default="low",
    )
    sample_size = fields.Integer()
    subject_asking_price = fields.Float(string="Subject Asking / List Price")
    subject_price_m2 = fields.Float()
    notes = fields.Text(
        default="Estimates only — based on asking prices, not guaranteed valuations."
    )

    def action_build_from_unit(self):
        self.ensure_one()
        unit = self.unit_id
        if not unit:
            return False
        subject = {
            "transaction_type": "sale",
            "category_code": "residential",
            "province": unit.project_id.city or "",
            "district": "",
            "neighborhood": "",
            "gross_area": unit.gross_m2 or 0,
            "rooms": "",
        }
        self.subject_asking_price = unit.list_price or 0.0
        if unit.gross_m2:
            self.subject_price_m2 = round((unit.list_price or 0) / unit.gross_m2, 2)
        self.project_id = unit.project_id

        candidates = self.env["tcrm.market.listing"].search([
            ("company_id", "=", self.company_id.id),
            ("state", "=", "active"),
            ("transaction_type", "=", "sale"),
            ("province", "ilike", unit.project_id.city or ""),
        ], limit=200)

        scored = []
        for cand in candidates:
            cdict = {
                "transaction_type": cand.transaction_type,
                "category_code": cand.category_code,
                "province": cand.province,
                "district": cand.district,
                "neighborhood": cand.neighborhood,
                "gross_area": cand.gross_area,
                "rooms": cand.rooms,
                "state": cand.state,
                "quality_score": cand.quality_score,
            }
            score, factors = comparable_score(subject, cdict)
            scored.append((score, factors, cand))
        scored.sort(key=lambda x: x[0], reverse=True)

        self.line_ids.unlink()
        lines = []
        prices = []
        for rank, (score, factors, cand) in enumerate(scored[:25], start=1):
            lines.append((0, 0, {
                "listing_id": cand.id,
                "rank": rank,
                "score": score,
                "included": rank <= 12,
                "explanation": ", ".join(factors),
            }))
            if rank <= 12:
                prices.append(cand.asking_price)
        self.line_ids = lines
        self.sample_size = len(prices)
        summary = summarize_prices(prices)
        if self.sample_size >= 10:
            self.confidence = "high"
        elif self.sample_size >= 5:
            self.confidence = "medium"
        else:
            self.confidence = "low"

        subject_pct = None
        if prices and self.subject_asking_price:
            below = sum(1 for p in prices if p <= self.subject_asking_price)
            subject_pct = round(100.0 * below / len(prices), 2)

        self.summary_json = json.dumps({
            "label": "Estimates based on asking prices",
            "comparable_asking_price": summary,
            "subject_asking_price": self.subject_asking_price,
            "subject_price_m2": self.subject_price_m2,
            "subject_percentile_vs_comps": subject_pct,
            "reasonable_asking_range": {
                "low": percentile(prices, 25),
                "high": percentile(prices, 75),
                "median": median(prices),
            },
            "sample_size": self.sample_size,
            "confidence": self.confidence,
            "analysis_date": fields.Date.context_today(self).isoformat(),
        }, default=str)
        return True


class TcrmMarketComparableLine(models.Model):
    _name = "tcrm.market.comparable.line"
    _description = "Market Comparable Line"
    _order = "rank, id"

    set_id = fields.Many2one("tcrm.market.comparable.set", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="set_id.company_id", store=True, index=True)
    listing_id = fields.Many2one("tcrm.market.listing", required=True, ondelete="cascade")
    rank = fields.Integer(default=99)
    score = fields.Float()
    included = fields.Boolean(default=True)
    explanation = fields.Char()
    asking_price = fields.Float(related="listing_id.asking_price", readonly=True)
    gross_price_m2 = fields.Float(related="listing_id.gross_price_m2", readonly=True)
    province = fields.Char(related="listing_id.province", readonly=True)
    district = fields.Char(related="listing_id.district", readonly=True)
