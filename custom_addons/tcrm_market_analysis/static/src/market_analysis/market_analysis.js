/** @odoo-module **/
import { Component, useState, onWillStart } from "@tcrm/owl";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

const SECTIONS = [
    { id: "overview", label: "Genel Bakış" },
    { id: "explorer", label: "Piyasa Gezgini" },
    { id: "map", label: "Harita" },
    { id: "comparables", label: "Emsal Analizi" },
    { id: "trends", label: "Trendler" },
    { id: "inventory", label: "Stok / Envanter" },
    { id: "saved", label: "Kaydedilmiş Analizler" },
    { id: "sources", label: "Veri Kaynakları" },
    { id: "imports", label: "İçe Aktarımlar" },
    { id: "quality", label: "Veri Kalitesi" },
];

export class TcrmMarketAnalysisApp extends Component {
    static template = "tcrm_market_analysis.App";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        const params = this.props.action?.params || {};
        this.state = useState({
            section: params.section || "overview",
            loading: true,
            overview: null,
            chart: null,
            listings: [],
            listingsTotal: 0,
            sources: [],
            saved: [],
            filters: {
                transaction_type: "",
                category_code: "",
                subcategory_code: "",
                province: params.province || "",
                district: "",
                neighborhood: "",
                price_min: "",
                price_max: "",
                rooms: "",
                heating: "",
                seller_type: "",
                furnished: "",
                state: "active",
            },
            provinceSuggestions: [],
            districtSuggestions: [],
            neighborhoodSuggestions: [],
            provinceQuery: params.province || "",
            districtQuery: "",
            neighborhoodQuery: "",
            viewMode: "table",
            saveName: "",
            lastError: "",
            label: "Asking prices only — not completed transactions.",
        });
        onWillStart(async () => {
            if (this.state.filters.province) {
                await this.onProvinceQuery(this.state.filters.province);
            }
            await this.refresh();
        });
    }

    get sections() {
        return SECTIONS;
    }

    setSection(id) {
        this.state.section = id;
        this.refresh();
    }

    domainFromFilters() {
        const d = [];
        const f = this.state.filters;
        if (f.state) d.push(["state", "=", f.state]);
        if (f.transaction_type) d.push(["transaction_type", "=", f.transaction_type]);
        if (f.category_code) d.push(["category_code", "=", f.category_code]);
        if (f.subcategory_code) d.push(["subcategory_code", "ilike", f.subcategory_code]);
        if (f.province) d.push(["province", "ilike", f.province]);
        if (f.district) d.push(["district", "ilike", f.district]);
        if (f.neighborhood) d.push(["neighborhood", "ilike", f.neighborhood]);
        if (f.price_min) d.push(["asking_price", ">=", Number(f.price_min)]);
        if (f.price_max) d.push(["asking_price", "<=", Number(f.price_max)]);
        if (f.rooms) d.push(["rooms", "ilike", f.rooms]);
        if (f.heating) d.push(["heating", "ilike", f.heating]);
        if (f.seller_type) d.push(["seller_type", "ilike", f.seller_type]);
        if (f.furnished) d.push(["furnished", "ilike", f.furnished]);
        return d;
    }

    async onProvinceQuery(q) {
        this.state.provinceQuery = q;
        const res = await rpc("/tcrm/market-analysis/geo/provinces", { query: q || "", limit: 20 });
        this.state.provinceSuggestions = res.records || [];
    }

    async selectProvince(item) {
        this.state.filters.province = item.name;
        this.state.provinceQuery = item.name;
        this.state.provinceSuggestions = [];
        this.state.filters.district = "";
        this.state.filters.neighborhood = "";
        this.state.districtQuery = "";
        this.state.neighborhoodQuery = "";
        this.state.neighborhoodSuggestions = [];
        const res = await rpc("/tcrm/market-analysis/geo/districts", {
            province: item.name,
            query: "",
            limit: 60,
        });
        this.state.districtSuggestions = res.records || [];
    }

    async onDistrictQuery(q) {
        this.state.districtQuery = q;
        if (!this.state.filters.province) {
            this.state.districtSuggestions = [];
            return;
        }
        const res = await rpc("/tcrm/market-analysis/geo/districts", {
            province: this.state.filters.province,
            query: q || "",
            limit: 40,
        });
        this.state.districtSuggestions = res.records || [];
    }

    async selectDistrict(item) {
        this.state.filters.district = item.name;
        this.state.districtQuery = item.name;
        this.state.districtSuggestions = [];
        this.state.filters.neighborhood = "";
        this.state.neighborhoodQuery = "";
        const res = await rpc("/tcrm/market-analysis/geo/neighborhoods", {
            province: this.state.filters.province,
            district: item.name,
            query: "",
            limit: 60,
        });
        this.state.neighborhoodSuggestions = res.records || [];
    }

    async onNeighborhoodQuery(q) {
        this.state.neighborhoodQuery = q;
        if (!this.state.filters.province || !this.state.filters.district) {
            this.state.neighborhoodSuggestions = [];
            return;
        }
        const res = await rpc("/tcrm/market-analysis/geo/neighborhoods", {
            province: this.state.filters.province,
            district: this.state.filters.district,
            query: q || "",
            limit: 40,
        });
        this.state.neighborhoodSuggestions = res.records || [];
    }

    selectNeighborhood(item) {
        this.state.filters.neighborhood = item.name;
        this.state.neighborhoodQuery = item.name;
        this.state.neighborhoodSuggestions = [];
    }

    async refresh() {
        this.state.loading = true;
        try {
            const domain = this.domainFromFilters();
            if (["overview", "trends", "inventory"].includes(this.state.section)) {
                this.state.overview = await rpc("/tcrm/market-analysis/overview", { domain });
                this.state.chart = await rpc("/tcrm/market-analysis/chart-data", { domain });
            }
            if (["explorer", "map", "quality"].includes(this.state.section)) {
                const res = await rpc("/tcrm/market-analysis/listings", { domain, limit: 80 });
                this.state.listings = res.records || [];
                this.state.listingsTotal = res.total || 0;
                if (this.state.section === "map") {
                    this.state.chart = await rpc("/tcrm/market-analysis/chart-data", { domain });
                }
            }
            if (this.state.section === "sources" || this.state.section === "imports") {
                const res = await rpc("/tcrm/market-analysis/sources", {});
                this.state.sources = res.records || [];
            }
            if (this.state.section === "saved") {
                this.state.saved = await this.orm.searchRead(
                    "tcrm.market.analysis",
                    [],
                    ["id", "name", "last_calculated_at", "visibility"],
                    { limit: 50 }
                );
            }
        } catch (e) {
            this.notification.add(e.message || String(e), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async applyFilters() {
        await this.refresh();
    }

    async scrapeSource(sourceId) {
        const res = await rpc("/tcrm/market-analysis/scrape-now", {
            source_id: sourceId || false,
            province: this.state.filters.province || this.state.provinceQuery || "",
            district: this.state.filters.district || this.state.districtQuery || "",
            neighborhood: this.state.filters.neighborhood || this.state.neighborhoodQuery || "",
            transaction_type: this.state.filters.transaction_type || "sale",
            category: this.state.filters.category_code === "land" ? "arsa"
                : this.state.filters.category_code === "commercial" ? "isyerleri" : "daire",
        });
        if (!res.ok) {
            this.notification.add(res.error || res.error_log || "Scrape blocked/failed", {
                type: "danger",
                sticky: true,
            });
            this.state.lastError = res.error || res.error_log || "";
        } else {
            this.notification.add(res.message || "Scrape finished", { type: "success" });
            this.state.lastError = "";
        }
        await this.refresh();
    }

    async loadDemo() {
        const res = await rpc("/tcrm/market-analysis/load-demo", {});
        if (res.error) {
            this.notification.add(res.error, { type: "danger" });
            return;
        }
        this.notification.add(res.message || `Loaded ${res.listings} listings`, { type: "success" });
        // Clear filters so demo rows are visible
        this.state.filters.province = "";
        this.state.filters.district = "";
        this.state.filters.neighborhood = "";
        this.state.provinceQuery = "";
        this.state.districtQuery = "";
        this.state.neighborhoodQuery = "";
        this.state.section = "explorer";
        await this.refresh();
    }

    async saveAnalysis() {
        const name = this.state.saveName || `Analiz ${new Date().toLocaleDateString("tr-TR")}`;
        const res = await rpc("/tcrm/market-analysis/save-analysis", {
            name,
            filter_json: this.state.filters,
        });
        if (res.error) {
            this.notification.add("Kayıt için Market Analyst yetkisi gerekir.", { type: "warning" });
            return;
        }
        this.notification.add(`Kaydedildi: ${res.name}`, { type: "success" });
        this.state.section = "saved";
        await this.refresh();
    }

    openBackendListings() {
        this.action.doAction("tcrm_market_analysis.action_tcrm_market_listing");
    }

    openSources() {
        this.action.doAction("tcrm_market_analysis.action_tcrm_market_source");
    }

    formatMoney(v) {
        if (v === null || v === undefined || v === false) return "—";
        return Number(v).toLocaleString("tr-TR", { maximumFractionDigits: 0 });
    }

    mapListings() {
        return (this.state.listings || []).filter((r) => r.latitude && r.longitude);
    }
}

registry.category("actions").add("tcrm_market_analysis.app", TcrmMarketAnalysisApp);
