/** @odoo-module **/
import { Component, useState, onWillStart, onMounted, onPatched, onWillUnmount, useRef } from "@tcrm/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";
import { serializeDate, today } from "@web/core/l10n/dates";
import { loadBundle } from "@web/core/assets";
import { download } from "@web/core/network/download";

const CHART_COLORS = [
    "#1B3F72", "#C9A84C", "#2ECC71", "#E74C3C", "#3498DB",
    "#9B59B6", "#F39C12", "#1ABC9C", "#E67E22", "#95A5A6",
];

const DATE_PRESETS = [
    { key: "today", label: "Bugün" },
    { key: "yesterday", label: "Dün" },
    { key: "last_7", label: "Son 7 Gün" },
    { key: "last_30", label: "Son 30 Gün" },
    { key: "this_week", label: "Bu Hafta" },
    { key: "last_week", label: "Geçen Hafta" },
    { key: "this_month", label: "Bu Ay" },
    { key: "last_month", label: "Geçen Ay" },
    { key: "this_year", label: "Bu Yıl" },
];

export class LeadReportDashboard extends Component {
    static template = "tcrm_lead_report.LeadReportDashboard";
    static components = { DateTimePicker };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.chartTimelineRef = useRef("chartTimeline");
        this.chartCalledRef = useRef("chartCalled");
        this.chartSourceRef = useRef("chartSource");
        this.chartOutcomesRef = useRef("chartOutcomes");
        this.chartCampaignRef = useRef("chartCampaign");
        this.chartSpendRef = useRef("chartSpend");
        this.chartSalespeopleRef = useRef("chartSalespeople");
        this._charts = {};

        const t = today();
        this.state = useState({
            loading: true,
            syncing: false,
            error: "",
            data: null,
            options: { sources: [], users: [], teams: [], stages: [], tags: [], campaigns: [] },
            filters: {},
            dateFrom: t.startOf("month"),
            dateTo: t,
            activePreset: "this_month",
        });

        this.datePresets = DATE_PRESETS;

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.loadOptions();
            await this.refresh();
        });

        onMounted(() => this._renderCharts());
        onPatched(() => this._renderCharts());
        onWillUnmount(() => this._destroyCharts());
    }

    get dateFromPickerProps() {
        return {
            type: "date",
            value: this.state.dateFrom,
            onChange: (val) => {
                this.state.dateFrom = val;
                this.state.activePreset = "custom";
            },
        };
    }

    get dateToPickerProps() {
        return {
            type: "date",
            value: this.state.dateTo,
            onChange: (val) => {
                this.state.dateTo = val;
                this.state.activePreset = "custom";
            },
        };
    }

    _payload() {
        return {
            ...this.state.filters,
            date_from: this.state.dateFrom ? serializeDate(this.state.dateFrom) : false,
            date_to: this.state.dateTo ? serializeDate(this.state.dateTo) : false,
        };
    }

    async loadOptions() {
        this.state.options = await this.orm.call("tcrm.lead.report", "get_filter_options", []);
    }

    async refresh() {
        this.state.loading = true;
        this.state.error = "";
        try {
            this.state.data = await this.orm.call(
                "tcrm.lead.report",
                "get_lead_report_data",
                [this._payload()]
            );
        } catch (err) {
            this.state.error = err.message || String(err);
            this.state.data = null;
        } finally {
            this.state.loading = false;
        }
    }

    async applyCustomDates() {
        this.state.activePreset = "custom";
        await this.refresh();
    }

    setDatePreset(key) {
        const t = today();
        let start = t;
        let end = t;
        switch (key) {
            case "today":
                start = t;
                end = t;
                break;
            case "yesterday":
                start = t.minus({ days: 1 });
                end = t.minus({ days: 1 });
                break;
            case "last_7":
                start = t.minus({ days: 6 });
                end = t;
                break;
            case "last_30":
                start = t.minus({ days: 29 });
                end = t;
                break;
            case "this_week":
                start = t.startOf("week");
                end = t.endOf("week");
                break;
            case "last_week":
                start = t.minus({ weeks: 1 }).startOf("week");
                end = t.minus({ weeks: 1 }).endOf("week");
                break;
            case "this_month":
                start = t.startOf("month");
                end = t;
                break;
            case "last_month":
                start = t.minus({ months: 1 }).startOf("month");
                end = t.minus({ months: 1 }).endOf("month");
                break;
            case "this_year":
                start = t.startOf("year");
                end = t;
                break;
            default:
                return;
        }
        this.state.dateFrom = start;
        this.state.dateTo = end;
        this.state.activePreset = key;
        this.refresh();
    }

    async onFilterChange(ev) {
        const filterKey = ev.target.dataset.filter;
        const value = ev.target.value;
        if (value) {
            this.state.filters[filterKey] = value;
        } else {
            delete this.state.filters[filterKey];
        }
        await this.refresh();
    }

    formatMoney(val) {
        if (val === null || val === undefined || val === false) {
            return "—";
        }
        return new Intl.NumberFormat("tr-TR", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
        }).format(val);
    }

    formatRatio(val) {
        if (val === null || val === undefined || val === false) {
            return "—";
        }
        return String(val);
    }

    async drill(drillKey, drillValue = false) {
        const action = await this.orm.call(
            "tcrm.lead.report",
            "open_drilldown",
            [drillKey, drillValue, this._payload()]
        );
        await this.action.doAction(action);
    }

    async drillRow(row) {
        if (row.drill_key) {
            await this.drill(row.drill_key, row.drill_value);
        }
    }

    async syncMarketing() {
        this.state.syncing = true;
        try {
            const result = await this.orm.call("tcrm.lead.report", "trigger_marketing_sync", []);
            this.notification.add(
                `Senkron tamamlandı: ${result.synced_rows || 0} satır`,
                { type: "success" }
            );
            await this.refresh();
        } catch (err) {
            this.notification.add(err.message || String(err), { type: "danger" });
        } finally {
            this.state.syncing = false;
        }
    }

    async exportReport(format) {
        try {
            const result = await this.orm.call(
                "tcrm.lead.report",
                "export_report",
                [this._payload(), format]
            );
            const content = Uint8Array.from(atob(result.content), (c) => c.charCodeAt(0));
            const blob = new Blob([content], { type: result.mimetype });
            download(blob, result.filename, result.mimetype);
        } catch (err) {
            this.notification.add(err.message || String(err), { type: "danger" });
        }
    }

    _destroyCharts() {
        for (const key of Object.keys(this._charts)) {
            if (this._charts[key]) {
                this._charts[key].destroy();
            }
        }
        this._charts = {};
    }

    _makeChart(key, canvasEl, config) {
        if (!canvasEl || typeof Chart === "undefined") {
            return;
        }
        if (this._charts[key]) {
            this._charts[key].destroy();
        }
        this._charts[key] = new Chart(canvasEl, config);
    }

    _renderCharts() {
        const data = this.state.data;
        if (!data || data.meta?.empty) {
            this._destroyCharts();
            return;
        }

        // Timeline
        const timeline = data.timeline?.points || [];
        this._makeChart("timeline", this.chartTimelineRef.el, {
            type: "line",
            data: {
                labels: timeline.map((p) => p.label),
                datasets: [{
                    label: "Lead",
                    data: timeline.map((p) => p.leads),
                    borderColor: CHART_COLORS[0],
                    backgroundColor: "rgba(27, 63, 114, 0.1)",
                    fill: true,
                    tension: 0.3,
                }],
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } },
        });

        // Called vs uncalled
        const calledData = data.called_vs_uncalled || [];
        this._makeChart("called", this.chartCalledRef.el, {
            type: "doughnut",
            data: {
                labels: calledData.map((d) => d.label),
                datasets: [{
                    data: calledData.map((d) => d.count),
                    backgroundColor: [CHART_COLORS[2], CHART_COLORS[3]],
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                onClick: (_ev, elements) => {
                    if (elements.length) {
                        const idx = elements[0].index;
                        this.drill(calledData[idx]?.key);
                    }
                },
            },
        });

        // Source donut
        const sources = data.sources || [];
        this._makeChart("source", this.chartSourceRef.el, {
            type: "doughnut",
            data: {
                labels: sources.map((s) => s.source),
                datasets: [{
                    data: sources.map((s) => s.leads),
                    backgroundColor: CHART_COLORS,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                onClick: (_ev, elements) => {
                    if (elements.length) {
                        const idx = elements[0].index;
                        this.drill("source", sources[idx]?.source_id);
                    }
                },
            },
        });

        // Call outcomes
        const outcomes = data.call_outcomes || [];
        this._makeChart("outcomes", this.chartOutcomesRef.el, {
            type: "bar",
            data: {
                labels: outcomes.map((o) => o.label),
                datasets: [{
                    label: "Lead",
                    data: outcomes.map((o) => o.count),
                    backgroundColor: CHART_COLORS[1],
                }],
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                onClick: (_ev, elements) => {
                    if (elements.length) {
                        const idx = elements[0].index;
                        this.drill("category", outcomes[idx]?.drill_value);
                    }
                },
            },
        });

        // Campaign bar
        const campaigns = (data.campaigns || []).slice(0, 10);
        this._makeChart("campaign", this.chartCampaignRef.el, {
            type: "bar",
            data: {
                labels: campaigns.map((c) => c.campaign?.substring(0, 20) || "—"),
                datasets: [
                    { label: "Lead", data: campaigns.map((c) => c.leads), backgroundColor: CHART_COLORS[0] },
                    { label: "Olumlu", data: campaigns.map((c) => c.positive), backgroundColor: CHART_COLORS[2] },
                    { label: "Randevu", data: campaigns.map((c) => c.appointment), backgroundColor: CHART_COLORS[4] },
                ],
            },
            options: { responsive: true, maintainAspectRatio: false },
        });

        // Spend vs leads combo
        if (data.meta?.can_view_spend && this.chartSpendRef.el) {
            this._makeChart("spend", this.chartSpendRef.el, {
                type: "bar",
                data: {
                    labels: campaigns.map((c) => c.campaign?.substring(0, 15) || "—"),
                    datasets: [
                        {
                            label: "Harcama",
                            data: campaigns.map((c) => c.spend || 0),
                            backgroundColor: CHART_COLORS[3],
                            yAxisID: "y",
                        },
                        {
                            label: "Lead",
                            data: campaigns.map((c) => c.leads),
                            type: "line",
                            borderColor: CHART_COLORS[0],
                            yAxisID: "y1",
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { position: "left" }, y1: { position: "right", grid: { drawOnChartArea: false } } },
                },
            });
        }

        // Salespeople
        const salespeople = (data.salespeople || []).slice(0, 10);
        this._makeChart("salespeople", this.chartSalespeopleRef.el, {
            type: "bar",
            data: {
                labels: salespeople.map((s) => s.name?.substring(0, 15) || "—"),
                datasets: [
                    { label: "Lead", data: salespeople.map((s) => s.leads), backgroundColor: CHART_COLORS[0] },
                    { label: "Arandı", data: salespeople.map((s) => s.called), backgroundColor: CHART_COLORS[2] },
                    { label: "Satış", data: salespeople.map((s) => s.sales), backgroundColor: CHART_COLORS[1] },
                ],
            },
            options: { responsive: true, maintainAspectRatio: false },
        });
    }
}

registry.category("actions").add("tcrm_lead_report.dashboard", LeadReportDashboard);
