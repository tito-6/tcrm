# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
import json
import logging

from tcrm import http
from tcrm.http import request

from ..services import tr_geo

_logger = logging.getLogger(__name__)


class TcrmMarketAnalysisController(http.Controller):
    """JSON-RPC helpers for the OWL Piyasa Analizi shell.

    Never accept a client db/company override that bypasses session mapping.
    """

    def _ensure_access(self):
        if not request.env.user.has_group("tcrm_market_analysis.group_market_viewer"):
            return {"error": "access_denied"}
        return None

    def _strip_db_kwargs(self, kwargs):
        kwargs.pop("db", None)
        kwargs.pop("dbname", None)
        kwargs.pop("company_id", None)  # never trust client company override
        return kwargs

    @http.route("/tcrm/market-analysis/overview", type="jsonrpc", auth="user")
    def overview(self, domain=None, **kwargs):
        denied = self._ensure_access()
        if denied:
            return denied
        self._strip_db_kwargs(kwargs)
        Listing = request.env["tcrm.market.listing"]
        metrics = Listing.get_overview_metrics(domain or [])
        metrics["tenant_db"] = request.env.cr.dbname
        metrics["company_id"] = request.env.company.id
        return metrics

    @http.route("/tcrm/market-analysis/listings", type="jsonrpc", auth="user")
    def listings(self, domain=None, limit=50, offset=0, order=None, **kwargs):
        denied = self._ensure_access()
        if denied:
            return denied
        self._strip_db_kwargs(kwargs)
        domain = list(domain or [])
        domain.append(("company_id", "in", request.env.companies.ids))
        Listing = request.env["tcrm.market.listing"]
        total = Listing.search_count(domain)
        rows = Listing.search_read(
            domain,
            [
                "id", "name", "title", "transaction_type", "category_code", "subcategory_code",
                "province", "district", "neighborhood", "asking_price", "currency_name",
                "gross_area", "net_area", "gross_price_m2", "rooms", "bedrooms", "bathrooms",
                "building_age", "floor", "total_floors", "heating", "kitchen", "balcony",
                "elevator", "parking", "furnished", "use_status", "in_compound",
                "mortgage_eligible", "title_deed_status", "seller_type",
                "source_listing_date", "permitted_source_url", "image_urls_json",
                "state", "quality_status", "duplicate_cluster", "latitude", "longitude",
                "first_observed_at", "last_observed_at", "media_count",
            ],
            limit=min(int(limit or 50), 200),
            offset=int(offset or 0),
            order=order or "last_observed_at desc",
        )
        for row in rows:
            try:
                row["image_urls"] = json.loads(row.get("image_urls_json") or "[]")
            except json.JSONDecodeError:
                row["image_urls"] = []
        return {
            "total": total,
            "records": rows,
            "label": "asking prices",
            "tenant_db": request.env.cr.dbname,
            "company_id": request.env.company.id,
        }

    @http.route("/tcrm/market-analysis/chart-data", type="jsonrpc", auth="user")
    def chart_data(self, domain=None, **kwargs):
        denied = self._ensure_access()
        if denied:
            return denied
        self._strip_db_kwargs(kwargs)
        domain = list(domain or []) + [("company_id", "in", request.env.companies.ids), ("state", "=", "active")]
        Listing = request.env["tcrm.market.listing"]
        rows = Listing.search_read(domain, ["asking_price", "gross_price_m2", "province", "category_code", "transaction_type"], limit=2000)
        if not rows:
            return {"empty": True, "message": "No authorized market data loaded"}
        by_province = {}
        for r in rows:
            key = r.get("province") or "—"
            by_province.setdefault(key, []).append(r["asking_price"] or 0)
        provinces = sorted(
            [{"name": k, "count": len(v), "avg_asking": round(sum(v) / len(v), 2) if v else 0} for k, v in by_province.items()],
            key=lambda x: -x["count"],
        )[:15]
        return {
            "empty": False,
            "by_province": provinces,
            "price_samples": [r["asking_price"] for r in rows if r.get("asking_price")][:200],
            "label": "asking prices",
        }

    @http.route("/tcrm/market-analysis/sources", type="jsonrpc", auth="user")
    def sources(self, **kwargs):
        denied = self._ensure_access()
        if denied:
            return denied
        self._strip_db_kwargs(kwargs)
        rows = request.env["tcrm.market.source"].search_read(
            [("company_id", "in", request.env.companies.ids)],
            [
                "id", "name", "source_type", "state", "authorization_state",
                "health", "last_success_at", "last_failure_at", "last_run_at",
                "rate_limit_state", "capabilities_display", "listing_count",
                "scrape_state", "scrape_progress", "scrape_progress_message",
                "filter_province", "filter_district", "filter_neighborhood",
                "filter_transaction", "filter_category", "schedule_enabled",
                "error_log",
            ],
        )
        return {"records": rows, "tenant_db": request.env.cr.dbname}

    @http.route("/tcrm/market-analysis/scrape-now", type="jsonrpc", auth="user")
    def scrape_now(self, source_id=None, **kwargs):
        if not request.env.user.has_group("tcrm_market_analysis.group_market_manager"):
            return {"error": "access_denied"}
        self._strip_db_kwargs(kwargs)
        Source = request.env["tcrm.market.source"]
        source = Source.browse(int(source_id)) if source_id else Source.browse()
        if not source:
            # Auto-create a public Sahibinden source for current company
            source = Source.create({
                "name": "Sahibinden Public",
                "source_type": "sahibinden",
                "company_id": request.env.company.id,
                "authorization_state": "authorized",
                "state": "enabled",
                "filter_transaction": kwargs.get("transaction_type") or "sale",
                "filter_category": kwargs.get("category") or "daire",
                "filter_province": kwargs.get("province") or "",
                "filter_district": kwargs.get("district") or "",
                "filter_neighborhood": kwargs.get("neighborhood") or "",
                "max_pages": 2,
                "max_records": 40,
            })
        if source.company_id.id not in request.env.companies.ids:
            return {"error": "not_found"}
        # Apply UI filters onto the source before scrape
        writes = {}
        if kwargs.get("province"):
            writes["filter_province"] = kwargs["province"]
        if kwargs.get("district"):
            writes["filter_district"] = kwargs["district"]
        if kwargs.get("neighborhood"):
            writes["filter_neighborhood"] = kwargs["neighborhood"]
        if kwargs.get("transaction_type"):
            writes["filter_transaction"] = "sale" if kwargs["transaction_type"] == "sale" else "rent"
        if kwargs.get("category"):
            writes["filter_category"] = kwargs["category"]
        if writes:
            source.write(writes)
        try:
            action = source.action_scrape_now()
            return {
                "ok": True,
                "job_id": action.get("res_id"),
                "scrape_state": source.scrape_state,
                "created": source.listing_count,
                "message": source.scrape_progress_message,
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "scrape_state": source.scrape_state,
                "error_log": source.error_log or str(exc),
                "source_id": source.id,
            }

    @http.route("/tcrm/market-analysis/load-demo", type="jsonrpc", auth="user")
    def load_demo(self, scenario=None, **kwargs):
        if not request.env.user.has_group("tcrm_market_analysis.group_market_manager"):
            # allow analysts too for empty-state recovery
            if not request.env.user.has_group("tcrm_market_analysis.group_market_analyst"):
                return {"error": "access_denied"}
        self._strip_db_kwargs(kwargs)
        from ..services.demo_seed import seed_company_demo
        company = request.env.company
        scen = scenario or ("istanbul" if (company.name or "").lower().find("ankara") < 0 else "ankara_izmir")
        env = request.env(context=dict(request.env.context, tcrm_market_allow_master_company_ops=True))
        request.env["ir.config_parameter"].sudo().set_param(
            "tcrm_market_analysis.allow_master_listings", "1"
        )
        source = seed_company_demo(env, company, scenario=scen)
        count = request.env["tcrm.market.listing"].search_count([
            ("company_id", "=", company.id),
        ])
        return {
            "ok": True,
            "source_id": source.id,
            "listings": count,
            "company_id": company.id,
            "message": "Demo listings loaded for current company (%s)." % count,
        }

    @http.route("/tcrm/market-analysis/geo/provinces", type="jsonrpc", auth="user")
    def geo_provinces(self, query="", limit=20, **kwargs):
        denied = self._ensure_access()
        if denied:
            return denied
        self._strip_db_kwargs(kwargs)
        return {"records": tr_geo.suggest_provinces(query or "", limit=int(limit or 20))}

    @http.route("/tcrm/market-analysis/geo/districts", type="jsonrpc", auth="user")
    def geo_districts(self, province="", query="", limit=40, **kwargs):
        denied = self._ensure_access()
        if denied:
            return denied
        self._strip_db_kwargs(kwargs)
        if not province:
            return {"records": [], "error": "province_required"}
        return {"records": tr_geo.suggest_districts(province, query or "", limit=int(limit or 40))}

    @http.route("/tcrm/market-analysis/geo/neighborhoods", type="jsonrpc", auth="user")
    def geo_neighborhoods(self, province="", district="", query="", limit=40, **kwargs):
        denied = self._ensure_access()
        if denied:
            return denied
        self._strip_db_kwargs(kwargs)
        if not province or not district:
            return {"records": [], "error": "province_and_district_required"}
        return {
            "records": tr_geo.suggest_neighborhoods(province, district, query or "", limit=int(limit or 40))
        }

    @http.route("/tcrm/market-analysis/geo/resolve", type="jsonrpc", auth="user")
    def geo_resolve(self, province="", district="", neighborhood="", **kwargs):
        denied = self._ensure_access()
        if denied:
            return denied
        self._strip_db_kwargs(kwargs)
        return tr_geo.build_filter_slugs(province, district, neighborhood)

    @http.route("/tcrm/market-analysis/save-analysis", type="jsonrpc", auth="user")
    def save_analysis(self, name, filter_json=None, **kwargs):
        if not request.env.user.has_group("tcrm_market_analysis.group_market_analyst"):
            return {"error": "access_denied"}
        self._strip_db_kwargs(kwargs)
        rec = request.env["tcrm.market.analysis"].create({
            "name": name,
            "filter_json": json.dumps(filter_json or {}),
            "company_id": request.env.company.id,
            "opportunity_id": kwargs.get("opportunity_id") or False,
            "unit_id": kwargs.get("unit_id") or False,
            "project_id": kwargs.get("project_id") or False,
        })
        rec.action_calculate()
        return {"id": rec.id, "name": rec.name}
