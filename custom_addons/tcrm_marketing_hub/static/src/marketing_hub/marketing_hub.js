/** @odoo-module **/
import { Component, useState, onWillStart, onMounted, onPatched, onWillUnmount, useRef } from "@tcrm/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { serializeDate, today } from "@web/core/l10n/dates";
import { loadBundle } from "@web/core/assets";

const SECTIONS = [
    { id: "overview", label: "Genel Bakış" },
    { id: "reports", label: "Raporlar" },
    { id: "assets", label: "Bağlı Varlıklar" },
    { id: "ads", label: "Kampanyalar" },
    { id: "leads", label: "Meta Leadler" },
    { id: "inbox", label: "Gelen Kutusu" },
    { id: "posts", label: "Gönderiler" },
];

const CHART_COLORS = {
    teal: "#0f766e",
    pink: "#db2777",
    blue: "#2563eb",
    violet: "#7c3aed",
    amber: "#ca8a04",
    slate: "#94a3b8",
};

export class TcrmMarketingHubApp extends Component {
    static template = "tcrm_marketing_hub.App";
    static components = { DateTimeInput };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.chartSourceRef = useRef("chartSource");
        this.chartDayRef = useRef("chartDay");
        this.chartStateRef = useRef("chartState");
        this.chartFormRef = useRef("chartForm");
        this.chartCreativeRef = useRef("chartCreative");
        this.chartSpendRef = useRef("chartSpend");
        this._charts = {};

        this.state = useState({
            section: "overview",
            loading: true,
            syncing: false,
            data: null,
            error: "",
            selectedAdAccountId: false,
            dateFrom: false,
            dateTo: false,
            leadSource: "",
            leadSearch: "",
            leadDetail: null,
            leadDetailLoading: false,
            drawerOpen: false,
            pageMgmt: null,
            pageMgmtLoading: false,
            pageMgmtSaving: false,
            pageSelectedIds: {},
            connectionTest: null,
        });

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.refresh();
            await this.loadPageManagement();
        });

        onMounted(() => {
            this._markHost();
            this._renderCharts();
        });

        onPatched(() => {
            this._renderCharts();
        });

        onWillUnmount(() => {
            this._unmarkHost();
            this._destroyCharts();
        });
    }

    _markHost() {
        const root = document.querySelector(".o_tcrm_mh_app");
        if (!root) {
            return;
        }
        const action = root.closest(".o_action");
        const content = root.closest(".o_content");
        if (action) {
            action.classList.add("o_tcrm_mh_host");
        }
        if (content) {
            content.classList.add("o_tcrm_mh_host");
        }
    }

    _unmarkHost() {
        document.querySelectorAll(".o_tcrm_mh_host").forEach((el) => {
            el.classList.remove("o_tcrm_mh_host");
        });
    }

    get sections() {
        return SECTIONS;
    }

    get stats() {
        return this.state.data?.stats || {};
    }

    get selectedAd() {
        return this.state.data?.selected_ad_account || null;
    }

    get charts() {
        return this.state.data?.charts || {};
    }

    get filteredLeads() {
        const leads = this.state.data?.leads || [];
        const q = (this.state.leadSearch || "").trim().toLowerCase();
        const src = this.state.leadSource;
        return leads.filter((l) => {
            if (src && l.source_platform !== src) {
                return false;
            }
            if (!q) {
                return true;
            }
            const hay = `${l.name} ${l.phone} ${l.email} ${l.company} ${l.form} ${l.ad_name} ${l.campaign_name}`.toLowerCase();
            return hay.includes(q);
        });
    }

    get filteredCampaigns() {
        return this.state.data?.campaigns || [];
    }

    sourceBadgeClass(key) {
        if (key === "instagram") return "o_tcrm_mh_badge o_tcrm_mh_badge_ig";
        if (key === "facebook") return "o_tcrm_mh_badge o_tcrm_mh_badge_fb";
        return "o_tcrm_mh_badge o_tcrm_mh_badge_meta";
    }

    creativeBadge(type) {
        if (type === "video") return "Video";
        if (type === "image") return "Görsel";
        return "—";
    }

    setSection(id) {
        this.state.section = id;
        if (id === "assets" && !this.state.pageMgmt) {
            this.loadPageManagement();
        }
    }

    _applyPageSelection(pageData) {
        this.state.pageMgmt = pageData;
        const selected = {};
        for (const acc of pageData?.accounts || []) {
            selected[acc.id] = Boolean(acc.sync_enabled);
        }
        this.state.pageSelectedIds = selected;
    }

    async loadPageManagement() {
        this.state.pageMgmtLoading = true;
        try {
            const data = await this.orm.call("tcrm.marketing.hub", "get_page_management", []);
            this._applyPageSelection(data);
        } catch (e) {
            this.notification.add(e?.data?.message || e?.message || String(e), { type: "danger" });
        } finally {
            this.state.pageMgmtLoading = false;
        }
    }

    togglePageSync(accountId) {
        if (!this.state.pageMgmt?.can_manage) {
            return;
        }
        this.state.pageSelectedIds[accountId] = !this.state.pageSelectedIds[accountId];
    }

    async savePageSelection() {
        if (!this.state.pageMgmt?.can_manage) {
            this.notification.add("Sayfa seçimini kaydetmek için yönetici yetkisi gerekir.", {
                type: "warning",
            });
            return;
        }
        this.state.pageMgmtSaving = true;
        try {
            const enabled = Object.entries(this.state.pageSelectedIds)
                .filter(([, on]) => on)
                .map(([id]) => Number(id));
            const data = await this.orm.call(
                "tcrm.marketing.hub",
                "set_page_selection",
                [enabled]
            );
            this._applyPageSelection(data);
            this.notification.add("Sayfa senkron atamaları kaydedildi.", { type: "success" });
            await this.refresh();
        } catch (e) {
            this.notification.add(e?.data?.message || e?.message || String(e), { type: "danger" });
        } finally {
            this.state.pageMgmtSaving = false;
        }
    }

    async refreshPages() {
        this.state.pageMgmtSaving = true;
        try {
            const data = await this.orm.call("tcrm.marketing.hub", "action_refresh_pages", []);
            this._applyPageSelection(data);
            this.notification.add(data.message || "Sayfalar yenilendi", { type: "success" });
            await this.refresh();
        } catch (e) {
            this.notification.add(e?.data?.message || e?.message || String(e), { type: "danger" });
        } finally {
            this.state.pageMgmtSaving = false;
        }
    }

    async testConnection() {
        this.state.pageMgmtSaving = true;
        this.state.connectionTest = null;
        try {
            const result = await this.orm.call(
                "tcrm.marketing.hub",
                "action_test_connection",
                []
            );
            this.state.connectionTest = result;
            this.notification.add(result.message || (result.success ? "Bağlantı OK" : "Hata"), {
                type: result.success ? "success" : "danger",
            });
        } catch (e) {
            this.notification.add(e?.data?.message || e?.message || String(e), { type: "danger" });
        } finally {
            this.state.pageMgmtSaving = false;
        }
    }

    async enablePage(accountId) {
        this.state.pageMgmtSaving = true;
        try {
            const data = await this.orm.call(
                "tcrm.marketing.hub",
                "action_enable_page",
                [accountId]
            );
            this._applyPageSelection(data);
        } catch (e) {
            this.notification.add(e?.data?.message || e?.message || String(e), { type: "danger" });
        } finally {
            this.state.pageMgmtSaving = false;
        }
    }

    async disablePage(accountId) {
        this.state.pageMgmtSaving = true;
        try {
            const data = await this.orm.call(
                "tcrm.marketing.hub",
                "action_disable_page",
                [accountId]
            );
            this._applyPageSelection(data);
        } catch (e) {
            this.notification.add(e?.data?.message || e?.message || String(e), { type: "danger" });
        } finally {
            this.state.pageMgmtSaving = false;
        }
    }

    _filterKwargs() {
        return {
            date_from: this.state.dateFrom ? serializeDate(this.state.dateFrom) : false,
            date_to: this.state.dateTo ? serializeDate(this.state.dateTo) : false,
        };
    }

    async refresh() {
        this.state.loading = true;
        this.state.error = "";
        try {
            const data = await this.orm.call(
                "tcrm.marketing.hub",
                "get_dashboard",
                [this.state.selectedAdAccountId || false],
                this._filterKwargs()
            );
            this.state.data = data;
            this.state.selectedAdAccountId = data.selected_ad_account_id || false;
        } catch (e) {
            this.state.error = e?.data?.message || e?.message || String(e);
        } finally {
            this.state.loading = false;
        }
    }

    async onSelectAdAccount(ev) {
        const id = Number(ev.target.value) || false;
        this.state.selectedAdAccountId = id;
        await this.refresh();
    }

    onDateFromChange(date) {
        this.state.dateFrom = date || false;
        this.refresh();
    }

    onDateToChange(date) {
        this.state.dateTo = date || false;
        this.refresh();
    }

    clearDates() {
        this.state.dateFrom = false;
        this.state.dateTo = false;
        this.refresh();
    }

    setPresetDays(days) {
        const end = today();
        this.state.dateTo = end;
        this.state.dateFrom = end.minus({ days: days - 1 });
        this.refresh();
    }

    setThisMonth() {
        const end = today();
        this.state.dateTo = end;
        this.state.dateFrom = end.startOf("month");
        this.refresh();
    }

    async fullSync() {
        this.state.syncing = true;
        this.state.error = "";
        try {
            const data = await this.orm.call(
                "tcrm.marketing.hub",
                "action_full_sync",
                [this.state.selectedAdAccountId || false],
                this._filterKwargs()
            );
            this.state.data = data;
            this.state.selectedAdAccountId = data.selected_ad_account_id || false;
            this.notification.add(data.sync_message || "Senkron tamamlandı", { type: "success" });
        } catch (e) {
            const msg = e?.data?.message || e?.message || String(e);
            const interrupted =
                /couldn't be established|interrupted|timeout|Gateway|504|502/i.test(msg);
            this.state.error = interrupted
                ? "Senkron zaman aşımına uğradı. “Gelen Kutusunu Çek” / “Leadleri Çek” / “Kampanyaları Çek” ile parçalı senkron deneyin."
                : msg;
            this.notification.add(this.state.error, { type: "danger" });
            // Refresh whatever already landed in DB
            try {
                await this.refresh();
            } catch (_e) {
                /* ignore */
            }
        } finally {
            this.state.syncing = false;
        }
    }

    async syncCampaigns() {
        this.state.syncing = true;
        try {
            const data = await this.orm.call(
                "tcrm.marketing.hub",
                "action_sync_campaigns_only",
                [this.state.selectedAdAccountId || false],
                this._filterKwargs()
            );
            this.state.data = data;
            this.notification.add(data.sync_message || "Kampanyalar senkronize edildi", { type: "success" });
            this.state.section = "ads";
        } catch (e) {
            this.notification.add(e?.data?.message || String(e), { type: "danger" });
        } finally {
            this.state.syncing = false;
        }
    }

    async syncLeads() {
        this.state.syncing = true;
        try {
            const data = await this.orm.call(
                "tcrm.marketing.hub",
                "action_sync_leads_only",
                [this.state.selectedAdAccountId || false],
                this._filterKwargs()
            );
            this.state.data = data;
            this.notification.add(data.sync_message || "Leadler senkronize edildi", { type: "success" });
            this.state.section = "leads";
        } catch (e) {
            this.notification.add(e?.data?.message || String(e), { type: "danger" });
        } finally {
            this.state.syncing = false;
        }
    }

    async syncInbox() {
        this.state.syncing = true;
        try {
            const data = await this.orm.call(
                "tcrm.marketing.hub",
                "action_sync_inbox_only",
                [this.state.selectedAdAccountId || false],
                this._filterKwargs()
            );
            this.state.data = data;
            this.notification.add(data.sync_message || "Gelen kutusu güncellendi", { type: "success" });
            this.state.section = "inbox";
        } catch (e) {
            this.notification.add(e?.data?.message || String(e), { type: "danger" });
        } finally {
            this.state.syncing = false;
        }
    }

    openInboxWindow() {
        this.action.doAction("tcrm_marketing_hub.action_tcrm_marketing_conversation");
    }

    async importPending() {
        this.state.syncing = true;
        try {
            const data = await this.orm.call(
                "tcrm.marketing.hub",
                "action_import_pending_leads",
                [this.state.selectedAdAccountId || false],
                this._filterKwargs()
            );
            this.state.data = data;
            this.notification.add(data.sync_message || "Aktarım tamam", { type: "success" });
        } catch (e) {
            this.notification.add(e?.data?.message || String(e), { type: "danger" });
        } finally {
            this.state.syncing = false;
        }
    }

    async openLeadPreview(id) {
        this.state.drawerOpen = true;
        this.state.leadDetailLoading = true;
        this.state.leadDetail = null;
        try {
            this.state.leadDetail = await this.orm.call(
                "tcrm.marketing.hub",
                "get_lead_detail",
                [id]
            );
        } catch (e) {
            this.notification.add(e?.data?.message || String(e), { type: "danger" });
            this.state.drawerOpen = false;
        } finally {
            this.state.leadDetailLoading = false;
        }
    }

    closeDrawer() {
        this.state.drawerOpen = false;
        this.state.leadDetail = null;
    }

    openCompose() {
        this.action.doAction("tcrm_marketing_hub.action_tcrm_marketing_compose");
    }

    openCreateAd() {
        this.action.doAction("tcrm_marketing_hub.action_tcrm_marketing_create_ad");
    }

    openCampaignsWindow() {
        this.action.doAction("tcrm_marketing_hub.action_tcrm_marketing_campaign");
    }

    openLeadsWindow() {
        this.action.doAction("tcrm_marketing_hub.action_tcrm_marketing_meta_lead");
    }

    openLeadGraph() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Lead Grafikleri",
            res_model: "tcrm.marketing.meta.lead",
            view_mode: "graph,pivot,list,form",
            views: [
                [false, "graph"],
                [false, "pivot"],
                [false, "list"],
                [false, "form"],
            ],
        });
    }

    openCrmLeads() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Meta CRM Leadleri",
            res_model: "crm.lead",
            view_mode: "list,form",
            domain: [["tag_ids.name", "=", "Meta Lead"]],
            views: [
                [false, "list"],
                [false, "form"],
            ],
        });
    }

    openMetaLead(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "tcrm.marketing.meta.lead",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openCrmLead(id) {
        if (!id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openConversation(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "tcrm.marketing.conversation",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openCampaign(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "tcrm.marketing.campaign",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openConnectFacebook() {
        this.action.doAction("tcrm_marketing_hub.action_tcrm_marketing_connect_facebook");
    }

    openConnectInstagram() {
        this.action.doAction("tcrm_marketing_hub.action_tcrm_marketing_connect_instagram");
    }

    _destroyCharts() {
        for (const key of Object.keys(this._charts)) {
            try {
                this._charts[key].destroy();
            } catch (_e) {
                /* ignore */
            }
            delete this._charts[key];
        }
    }

    _makeChart(key, canvasEl, config) {
        if (!canvasEl || typeof Chart === "undefined") {
            return;
        }
        if (this._charts[key]) {
            try {
                this._charts[key].destroy();
            } catch (_e) {
                /* ignore */
            }
        }
        this._charts[key] = new Chart(canvasEl, config);
    }

    _baseOptions(title) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { boxWidth: 12, font: { size: 11 } },
                },
                title: {
                    display: Boolean(title),
                    text: title || "",
                    font: { size: 13, weight: "600" },
                    color: "#13221f",
                },
            },
        };
    }

    _renderCharts() {
        if (this.state.loading || !this.state.data) {
            return;
        }
        if (this.state.section !== "overview" && this.state.section !== "reports") {
            return;
        }
        const c = this.charts;
        if (!c || !Object.keys(c).length) {
            return;
        }

        if (this.chartSourceRef.el) {
            this._makeChart("source", this.chartSourceRef.el, {
                type: "doughnut",
                data: {
                    labels: c.by_source?.labels || [],
                    datasets: [{
                        data: c.by_source?.values || [],
                        backgroundColor: c.by_source?.colors || [
                            CHART_COLORS.pink, CHART_COLORS.blue, CHART_COLORS.teal,
                        ],
                        borderWidth: 0,
                    }],
                },
                options: {
                    ...this._baseOptions("Kaynak Dağılımı"),
                    cutout: "58%",
                },
            });
        }

        if (this.chartDayRef.el) {
            this._makeChart("day", this.chartDayRef.el, {
                type: "bar",
                data: {
                    labels: c.by_day?.labels || [],
                    datasets: [{
                        label: "Lead",
                        data: c.by_day?.values || [],
                        backgroundColor: "rgba(15, 118, 110, 0.75)",
                        borderRadius: 4,
                    }],
                },
                options: {
                    ...this._baseOptions("Günlük Lead Trendı"),
                    plugins: {
                        ...this._baseOptions("Günlük Lead Trendı").plugins,
                        legend: { display: false },
                    },
                    scales: {
                        x: { grid: { display: false } },
                        y: { beginAtZero: true, ticks: { precision: 0 } },
                    },
                },
            });
        }

        if (this.chartStateRef.el) {
            this._makeChart("state", this.chartStateRef.el, {
                type: "doughnut",
                data: {
                    labels: c.by_state?.labels || [],
                    datasets: [{
                        data: c.by_state?.values || [],
                        backgroundColor: c.by_state?.colors || [
                            CHART_COLORS.amber, "#16a34a", CHART_COLORS.slate,
                        ],
                        borderWidth: 0,
                    }],
                },
                options: {
                    ...this._baseOptions("CRM Durumu"),
                    cutout: "55%",
                },
            });
        }

        if (this.chartFormRef.el) {
            this._makeChart("form", this.chartFormRef.el, {
                type: "bar",
                data: {
                    labels: c.by_form?.labels || [],
                    datasets: [{
                        label: "Lead",
                        data: c.by_form?.values || [],
                        backgroundColor: "rgba(37, 99, 235, 0.7)",
                        borderRadius: 4,
                    }],
                },
                options: {
                    ...this._baseOptions("Formlara Göre"),
                    indexAxis: "y",
                    plugins: {
                        ...this._baseOptions("Formlara Göre").plugins,
                        legend: { display: false },
                    },
                    scales: {
                        x: { beginAtZero: true, ticks: { precision: 0 } },
                        y: { grid: { display: false } },
                    },
                },
            });
        }

        if (this.chartCreativeRef.el) {
            this._makeChart("creative", this.chartCreativeRef.el, {
                type: "doughnut",
                data: {
                    labels: c.by_creative?.labels || [],
                    datasets: [{
                        data: c.by_creative?.values || [],
                        backgroundColor: c.by_creative?.colors || [
                            CHART_COLORS.violet, "#0891b2", CHART_COLORS.slate,
                        ],
                        borderWidth: 0,
                    }],
                },
                options: {
                    ...this._baseOptions("Kreatif Tipi"),
                    cutout: "55%",
                },
            });
        }

        if (this.chartSpendRef.el) {
            this._makeChart("spend", this.chartSpendRef.el, {
                type: "bar",
                data: {
                    labels: c.campaign_spend?.labels || [],
                    datasets: [{
                        label: "Harcama",
                        data: c.campaign_spend?.values || [],
                        backgroundColor: "rgba(219, 39, 119, 0.65)",
                        borderRadius: 4,
                    }],
                },
                options: {
                    ...this._baseOptions("Kampanya Harcaması"),
                    plugins: {
                        ...this._baseOptions("Kampanya Harcaması").plugins,
                        legend: { display: false },
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: { maxRotation: 40, minRotation: 0 },
                        },
                        y: { beginAtZero: true },
                    },
                },
            });
        }
    }
}

registry.category("actions").add("tcrm_marketing_hub.app", TcrmMarketingHubApp);
