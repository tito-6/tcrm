/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";
import { deserializeDate, serializeDate, today } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { loadJS } from "@web/core/assets";
import { Component, onWillStart, useState, useRef, useEffect, onWillUnmount } from "@tcrm/owl";

export class PropertioReportsCenter extends Component {
    static template = "tcrm_propertio.PropertioReportsCenter";
    static components = { DateTimePicker };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            reports: [],
            recent: [],
            templates: [],
            optionsData: {},
            selectedKey: null,
            payload: null,
            loading: false,
            search: "",
            category: "All",
            viewMode: "table",
            filters: {
                date_from: "",
                date_to: "",
                project_id: "",
                block_id: "",
                unit_type_id: "",
                customer_id: "",
                salesperson_id: "",
                fiscal_year: "",
                broker_id: "",
                currency_id: "",
                sales_status: "",
                payment_status: "",
                unit_state: "",
            },
            dateFrom: false,
            dateTo: false,
            options: {
                columns: [],
                group_by: "",
                sort_by: "",
                sort_dir: "desc",
                chart_type: "bar",
                accounting_view: "accrual",
                chart_group_by: "",
                chart_value: "",
                chart_limit: 12,
            },
        });
        this.chartCanvas = useRef("chartCanvas");
        this.chartInstance = null;

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.loadCatalog();
        });

        useEffect(() => {
            if (this.state.viewMode === "chart" && this.state.payload && this.state.payload.chart && this.state.payload.chart.length > 0) {
                this.renderChart();
            } else if (this.chartInstance) {
                this.chartInstance.destroy();
                this.chartInstance = null;
            }
        }, () => [this.state.viewMode, this.state.payload, this.state.options.chart_type]);

        onWillUnmount(() => {
            if (this.chartInstance) {
                this.chartInstance.destroy();
            }
        });
    }

    renderChart() {
        if (this.chartInstance) {
            this.chartInstance.destroy();
            this.chartInstance = null;
        }
        if (!this.chartCanvas.el) return;

        const data = this.state.payload.chart;
        const labels = data.map(d => d.label);
        const values = data.map(d => d.value);

        // Generate dynamic colors based on values
        const colors = [
            '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
            '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#5470c6'
        ];
        
        const backgroundColors = data.map((_, i) => colors[i % colors.length]);

        const config = {
            type: this.state.options.chart_type === 'donut' ? 'doughnut' : this.state.options.chart_type,
            data: {
                labels: labels,
                datasets: [{
                    label: this.columnLabel(this.state.options.chart_value || this.selectedReport.chart_value),
                    data: values,
                    backgroundColor: backgroundColors,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                    }
                }
            }
        };

        this.chartInstance = new window.Chart(this.chartCanvas.el, config);
    }

    async loadCatalog() {
        const [catalog, optionsData] = await Promise.all([
            this.orm.call("propertio.report.engine", "list_reports", []),
            this.orm.call("propertio.report.engine", "get_filter_options", []),
        ]);
        this.state.reports = catalog.reports || [];
        this.state.recent = catalog.recent || [];
        this.state.templates = catalog.templates || [];
        this.state.optionsData = optionsData || {};
        this.state.selectedKey = this.state.reports[0]?.key || null;
        if (this.state.selectedKey) {
            await this.runReport();
        }
    }

    get selectedReport() {
        return this.state.reports.find((report) => report.key === this.state.selectedKey) || {};
    }

    get categories() {
        return ["All", ...new Set(this.state.reports.map((report) => report.category))];
    }

    /** Numbered category options from backend (category_number / category_label). */
    get categoryOptions() {
        const seen = new Map();
        for (const report of this.state.reports) {
            if (!report.category || seen.has(report.category)) {
                continue;
            }
            seen.set(report.category, {
                key: report.category,
                label: report.category_label || report.category,
                number: report.category_number || 0,
            });
        }
        return [...seen.values()].sort((a, b) => (a.number || 0) - (b.number || 0));
    }

    get filteredReports() {
        const needle = (this.state.search || "").toLowerCase();
        return this.state.reports.filter((report) => {
            const categoryOk = this.state.category === "All" || report.category === this.state.category;
            const searchOk = !needle || `${report.name} ${report.name_tr} ${report.name_en} ${report.name_ar} ${report.category_label}`.toLowerCase().includes(needle);
            return categoryOk && searchOk;
        });
    }

    reportsInCategory(categoryKey) {
        return this.state.reports.filter((report) => {
            if (this.state.category !== "All" && this.state.category !== categoryKey) {
                return false;
            }
            return report.category === categoryKey;
        });
    }

    async onReportSelect(ev) {
        const key = ev.target.value || "";
        if (key) {
            await this.selectReport(key);
        }
    }

    get favoriteReports() {
        return this.state.reports.filter((report) => report.favorite);
    }

    get recentReports() {
        return this.state.recent.map((key) => this.state.reports.find((report) => report.key === key)).filter(Boolean);
    }

    get visibleColumns() {
        return this.state.payload?.columns || [];
    }

    get selectedFilterFields() {
        return this.selectedReport.filter_fields || [];
    }

    get hasDateRangeFilter() {
        return this.selectedFilterFields.some((field) => field.type === "date_range");
    }

    get selectFilterFields() {
        return this.selectedFilterFields.filter((field) => field.type !== "date_range");
    }

    get chartTypes() {
        const configured = this.selectedReport.chart_options?.types || [];
        return [...new Set(["bar", "line", "pie", ...configured])];
    }

    get chartGroupOptions() {
        const configured = this.selectedReport.chart_options?.groups || [];
        const columns = this.visibleColumns.map((col) => col.key);
        return [...new Set([...configured, ...columns])].filter(Boolean);
    }

    get chartValueOptions() {
        const configured = this.selectedReport.chart_options?.values || [];
        const numeric = this.visibleColumns.filter((col) => col.type === "number").map((col) => col.key);
        return [...new Set([...configured, ...numeric])].filter(Boolean);
    }

    get rowLimitMessage() {
        const count = this.state.payload?.row_count || 0;
        return count > 500 ? _t("İlk 500 satır gösteriliyor. Dışa aktarımlar filtrelenmiş sonucu içerir.") : "";
    }

    get dateFromPickerProps() {
        return {
            type: "date",
            showWeekNumbers: false,
            maxPrecision: "days",
            daysOfWeekFormat: "narrow",
            value: this.state.dateFrom || false,
            onSelect: (date) => {
                this.state.dateFrom = date || false;
                this.state.filters.date_from = date ? serializeDate(date) : "";
            },
        };
    }

    get dateToPickerProps() {
        return {
            type: "date",
            showWeekNumbers: false,
            maxPrecision: "days",
            daysOfWeekFormat: "narrow",
            value: this.state.dateTo || false,
            onSelect: (date) => {
                this.state.dateTo = date || false;
                this.state.filters.date_to = date ? serializeDate(date) : "";
            },
        };
    }

    async selectReport(reportKey) {
        this.state.selectedKey = reportKey;
        this.state.options.columns = [];
        this.state.options.group_by = "";
        this.state.options.sort_by = "";
        this.state.options.chart_type = this.selectedReport.chart_options?.types?.[0] || "bar";
        this.state.options.chart_group_by = this.selectedReport.chart_axis || "";
        this.state.options.chart_value = this.selectedReport.chart_value || "";
        await this.runReport();
    }

    async runReport() {
        if (!this.state.selectedKey) {
            return;
        }
        this.state.loading = true;
        try {
            const filters = this._compact(this.state.filters);
            const options = { ...this.state.options };
            if (!options.columns.length) {
                delete options.columns;
            }
            this.state.payload = await this.orm.call("propertio.report.engine", "run_report", [
                this.state.selectedKey,
                filters,
                options,
            ]);
            this.state.options.columns = this.state.payload.columns.map((column) => column.key);
        } catch (error) {
            console.error("[Propertio Reports Center]", error);
            this.notification.add(_t("Rapor oluşturulamadı. Ayrıntılar için sunucu günlüklerine bakın."), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async toggleFavorite(report, ev) {
        ev.stopPropagation();
        const value = await this.orm.call("propertio.report.engine", "toggle_favorite", [report.key]);
        report.favorite = value;
    }

    setFilter(name, ev) {
        this.state.filters[name] = ev.target.value || "";
    }

    setSearch(ev) {
        this.state.search = ev.target.value || "";
    }

    async setCategory(ev) {
        this.state.category = ev.target.value || "All";
        const visible = this.filteredReports;
        if (!visible.some((report) => report.key === this.state.selectedKey)) {
            if (visible[0]) {
                await this.selectReport(visible[0].key);
            } else {
                this.state.selectedKey = null;
                this.state.payload = null;
            }
        }
    }

    setOption(name, ev) {
        this.state.options[name] = ev.target.value || "";
    }

    async setChartType(type) {
        this.state.options.chart_type = type;
        await this.runReport();
    }

    async setAccountingView(view) {
        this.state.options.accounting_view = view;
        await this.runReport();
    }

    filterOptions(field) {
        return this.state.optionsData[field.options_key] || [];
    }

    chartPercent(point) {
        const pct = point.percent || 0;
        return `${Math.max(0, Math.min(100, pct))}%`;
    }

    toggleColumn(columnKey, ev) {
        const selected = new Set(this.state.options.columns);
        if (ev.target.checked) {
            selected.add(columnKey);
        } else {
            selected.delete(columnKey);
        }
        this.state.options.columns = [...selected];
    }

    async sortBy(columnKey) {
        if (this.state.options.sort_by === columnKey) {
            this.state.options.sort_dir = this.state.options.sort_dir === "asc" ? "desc" : "asc";
        } else {
            this.state.options.sort_by = columnKey;
            this.state.options.sort_dir = "desc";
        }
        await this.runReport();
    }

    async saveTemplate() {
        const name = window.prompt(_t("Rapor ön ayar adı"));
        if (!name) {
            return;
        }
        const template = await this.orm.call("propertio.report.engine", "save_template", [
            this.state.selectedKey,
            name,
            { filters: this._compact(this.state.filters), options: this.state.options },
            false,
        ]);
        this.state.templates.push(template);
        this.notification.add(_t("Rapor ön ayarı kaydedildi."), { type: "success" });
    }

    async applyTemplate(template) {
        this.state.selectedKey = template.report_key;
        Object.assign(this.state.filters, template.options.filters || {});
        Object.assign(this.state.options, template.options.options || {});
        this._syncPickerDatesFromFilters();
        await this.runReport();
    }

    async resetFilters() {
        this.state.filters = {};
        this.state.dateFrom = false;
        this.state.dateTo = false;
        this.state.options.group_by = "";
        this.state.options.chart_group_by = "";
        this.state.options.chart_value = "";
        await this.runReport();
    }

    async setQuickDate(period) {
        const t = today();
        let start, end;
        
        switch (period) {
            case 'this_week':
                start = t.startOf("week");
                end = t.endOf("week");
                break;
            case 'last_week':
                start = t.minus({ weeks: 1 }).startOf("week");
                end = t.minus({ weeks: 1 }).endOf("week");
                break;
            case 'this_month':
                start = t.startOf("month");
                end = t.endOf("month");
                break;
            case 'last_month':
                start = t.minus({ months: 1 }).startOf("month");
                end = t.minus({ months: 1 }).endOf("month");
                break;
            case 'this_quarter':
                start = t.startOf("quarter");
                end = t.endOf("quarter");
                break;
            case 'last_quarter':
                start = t.minus({ quarters: 1 }).startOf("quarter");
                end = t.minus({ quarters: 1 }).endOf("quarter");
                break;
            case 'this_year':
                start = t.startOf("year");
                end = t.endOf("year");
                break;
            case 'last_year':
                start = t.minus({ years: 1 }).startOf("year");
                end = t.minus({ years: 1 }).endOf("year");
                break;
            case 'all_time':
                this.state.dateFrom = false;
                this.state.dateTo = false;
                this.state.filters.date_from = "";
                this.state.filters.date_to = "";
                await this.runReport();
                return;
        }

        this.state.dateFrom = start;
        this.state.dateTo = end;
        this.state.filters.date_from = serializeDate(start);
        this.state.filters.date_to = serializeDate(end);
        await this.runReport();
    }

    async duplicateTemplate(template, ev) {
        ev.stopPropagation();
        const copy = await this.orm.call("propertio.report.engine", "duplicate_template", [template.id]);
        this.state.templates.push(copy);
    }

    async deleteTemplate(template, ev) {
        ev.stopPropagation();
        await this.orm.call("propertio.report.engine", "delete_template", [template.id]);
        this.state.templates = this.state.templates.filter((item) => item.id !== template.id);
    }

    async drill(row) {
        const ids = row._ids || (row._id ? [row._id] : []);
        if (!ids.length) {
            return;
        }
        const action = await this.orm.call("propertio.report.engine", "open_drilldown_action", [
            this.state.selectedKey,
            ids,
        ]);
        await this.action.doAction(action);
    }

    exportUrl(format) {
        const encode = (value) => {
            const text = JSON.stringify(value || {});
            return btoa(unescape(encodeURIComponent(text))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
        };
        const filters = encode(this._compact(this.state.filters));
        const options = encode(this.state.options);
        return `/propertio/reports/export/${this.state.selectedKey}/${format}?filters=${filters}&options=${options}`;
    }

    formatValue(value) {
        if (typeof value === "number") {
            return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value);
        }
        return value === false || value === null || value === undefined ? "" : value;
    }

    columnLabel(key) {
        const column = (this.state.payload?.columns || []).find((item) => item.key === key);
        return column?.label || key;
    }

    barWidth(point) {
        const values = (this.state.payload?.chart || []).map((item) => item.value || 0);
        const max = Math.max(1, ...values);
        return `${Math.max(4, Math.min(100, ((point.value || 0) / max) * 100))}%`;
    }

    _compact(obj) {
        return Object.fromEntries(Object.entries(obj || {}).filter(([, value]) => value !== "" && value !== false && value !== null));
    }

    _syncPickerDatesFromFilters() {
        this.state.dateFrom = this.state.filters.date_from ? deserializeDate(this.state.filters.date_from) : false;
        this.state.dateTo = this.state.filters.date_to ? deserializeDate(this.state.filters.date_to) : false;
    }
}

registry.category("actions").add("propertio.reports_center", PropertioReportsCenter);
